import csv
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select

from app.data.schema import (
    RouteStop,
    TransitRoute,
    TransitScheduleImport,
    TransitServiceProfile,
    TransitStop,
    TransitStopTime,
    TransitTrip,
)
from app.data.transport_pilot import (
    NormalizedSchedulePlan,
    PilotRoute,
    PilotStop,
    PilotValidationError,
    ScheduleRouteInput,
    ScheduleTripInput,
    ScheduleTripStop,
    build_normalized_schedule_plan,
    import_normalized_schedule,
    import_pilot_route,
    load_pilot_route,
    rollback_normalized_schedule,
)


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _snapshot(tmp_path: Path, *, exact_second: bool = True) -> Path:
    provenance = {
        "source_file": "map.pdf",
        "source_page": "7",
        "effective_from": "2025-12-01",
        "effective_until": "",
        "source_last_updated": "",
        "freshness_as_of": "2026-09-12",
        "freshness_status": "unverified",
    }
    _write(
        tmp_path / "bus_stop_times.csv",
        [
            {
                "trip_id": "trip-1",
                "route_id": "EV3",
                "stop_sequence": sequence,
                "stop_id": stop_id,
                "stop_name_raw": name,
            }
            for sequence, stop_id, name in [
                (1, "stop-a", "A"),
                (2, "stop-b", "B"),
                (3, "stop-c", "C"),
            ]
        ],
    )
    _write(
        tmp_path / "stops.csv",
        [
            {
                "stop_id": "stop-a",
                "match_status": "matched_exact",
                "matched_activity_id": "activity-a",
            },
            {
                "stop_id": "stop-b",
                "match_status": "matched_exact" if exact_second else "review_fuzzy",
                "matched_activity_id": "activity-b" if exact_second else "",
            },
            {
                "stop_id": "stop-c",
                "match_status": "matched_exact",
                "matched_activity_id": "activity-c",
            },
        ],
    )
    _write(
        tmp_path / "activity_stop_catalog.csv",
        [
            {
                "source_id": activity_id,
                "name": name,
                "longitude": longitude,
                "latitude": latitude,
                "observed_at": "2025-01-01T00:00:00Z",
            }
            for activity_id, name, longitude, latitude in [
                ("activity-a", "Halte A", 110.3, -7.8),
                ("activity-b", "Halte B", 110.31, -7.81),
                ("activity-c", "Halte C", 110.32, -7.82),
            ]
        ],
    )
    _write(
        tmp_path / "service_profiles.csv",
        [
            {
                "route_id": "EV3",
                "basis": "timetable_header",
                "headway_min_minutes": "25",
                "headway_max_minutes": "55",
                **provenance,
            }
        ],
    )
    _write(
        tmp_path / "fares.csv",
        [
            {
                "service_id": "transjogja",
                "payment_method": "cash",
                "fare_min": "3500",
                "fare_max": "3500",
            }
        ],
    )
    _write(
        tmp_path / "bus_segments.csv",
        [
            {
                "route_id": "EV3",
                "from_stop_sequence": "1",
                "to_stop_sequence": "2",
                "from_stop_id": "stop-a",
                "to_stop_id": "stop-b",
                "travel_time_s": "180",
            },
            {
                "route_id": "EV3",
                "from_stop_sequence": "2",
                "to_stop_sequence": "3",
                "from_stop_id": "stop-b",
                "to_stop_id": "stop-c",
                "travel_time_s": "240",
            },
        ],
    )
    return tmp_path


def test_load_pilot_route_preserves_effective_date_and_segment_time(tmp_path: Path) -> None:
    route = load_pilot_route(_snapshot(tmp_path))

    assert route.headway_min == 40
    assert route.fare_idr == 3500
    assert route.provenance["effective_from"] == "2025-12-01"
    assert route.provenance["freshness_status"] == "unverified"
    assert route.stops[1].travel_time_from_prev_s == 180


def test_load_pilot_route_requires_reviewed_activity_for_every_stop(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, exact_second=False)

    with pytest.raises(PilotValidationError, match="1 unresolved stop positions"):
        load_pilot_route(snapshot)


def test_approved_review_resolves_activity_coordinate(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, exact_second=False)
    reviews = tmp_path / "reviews.csv"
    _write(
        reviews,
        [
            {
                "route_id": "EV3",
                "stop_id": "stop-b",
                "candidate_activity_id": "activity-b",
                "decision": "approved",
                "reviewer": "tester",
                "reviewed_at": "2026-09-12",
                "notes": "same shelter",
            }
        ],
    )

    route = load_pilot_route(snapshot, reviews_path=reviews)

    assert route.stops[1].match_status == "reviewed_activity"
    assert route.stops[1].longitude == 110.31


def test_skip_unresolved_stop_preserves_through_travel_time(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, exact_second=False)

    route = load_pilot_route(
        snapshot,
        skip_stop_sequences={2},
        skip_reason="survey window closed before submission",
    )

    assert [stop.normalized_stop_id for stop in route.stops] == ["stop-a", "stop-c"]
    assert route.stops[1].travel_time_from_prev_s == 420
    assert route.skipped_stop_sequences == (2,)
    assert route.provenance["skipped_stop_sequences"] == "2"
    assert "skip_reason=survey window closed before submission" in route.source


async def test_import_pilot_route_is_idempotent(db_session) -> None:
    provenance = {
        "source_file": "map.pdf",
        "source_page": "7",
        "effective_from": "2025-12-01",
        "effective_until": "",
        "source_last_updated": "",
        "freshness_as_of": "2026-09-12",
        "freshness_status": "unverified",
    }
    route = PilotRoute(
        route_id="EV3",
        operator="TransJogja",
        mode="bus",
        headway_min=40,
        fare_idr=3500,
        source="transport-pdf:EV3;effective_from=2025-12-01;freshness_status=unverified",
        provenance=provenance,
        stops=(
            PilotStop(
                sequence=1,
                normalized_stop_id="stop-a",
                name="A",
                activity_id="pilot-activity-a",
                activity_name="Halte A",
                longitude=110.3,
                latitude=-7.8,
                activity_observed_at="2025-01-01T00:00:00Z",
                travel_time_from_prev_s=None,
                match_status="matched_exact",
                review=None,
            ),
            PilotStop(
                sequence=2,
                normalized_stop_id="stop-b",
                name="B",
                activity_id="pilot-activity-b",
                activity_name="Halte B",
                longitude=110.31,
                latitude=-7.81,
                activity_observed_at="2025-01-01T00:00:00Z",
                travel_time_from_prev_s=180,
                match_status="matched_exact",
                review=None,
            ),
        ),
    )
    original_raw = {"description": "Survey data", "medias": ["halte-a.jpg"]}
    for values in (
        {
            "external_id": "pilot-activity-a",
            "name": "Halte A",
            "mode": "bus",
            "operator": "TransJogja",
            "raw": original_raw,
            "source": "mapid_activities",
            "geom": func.ST_SetSRID(func.ST_MakePoint(110.3, -7.8), 4326),
        },
        {
            "external_id": "pilot-activity-b",
            "name": "Halte B",
            "mode": "bus",
            "operator": "TransJogja",
            "raw": {"description": "Survey data B"},
            "source": "mapid_activities",
            "geom": func.ST_SetSRID(func.ST_MakePoint(110.31, -7.81), 4326),
        },
    ):
        await db_session.execute(insert(TransitStop).values(**values))
    await db_session.commit()

    first = await import_pilot_route(db_session, route)
    second = await import_pilot_route(db_session, route)

    assert first["route_id"] == second["route_id"]
    assert await db_session.scalar(select(func.count()).select_from(TransitRoute)) == 1
    assert await db_session.scalar(select(func.count()).select_from(TransitStop)) == 2
    assert await db_session.scalar(select(func.count()).select_from(RouteStop)) == 2
    assert (
        await db_session.scalar(
            select(TransitStop.raw).where(TransitStop.external_id == "pilot-activity-a")
        )
        == original_raw
    )


async def test_import_pilot_route_never_creates_missing_activity_stops(db_session) -> None:
    route = PilotRoute(
        route_id="EV3",
        operator="TransJogja",
        mode="bus",
        headway_min=40,
        fare_idr=3500,
        source="transport-pdf:EV3;freshness_status=unverified",
        provenance={"freshness_status": "unverified"},
        stops=(
            PilotStop(
                sequence=1,
                normalized_stop_id="stop-a",
                name="A",
                activity_id="missing-activity",
                activity_name="Halte A",
                longitude=110.3,
                latitude=-7.8,
                activity_observed_at="2025-01-01T00:00:00Z",
                travel_time_from_prev_s=None,
                match_status="matched_exact",
                review=None,
            ),
        ),
    )

    with pytest.raises(PilotValidationError, match="not ingested into transit_stops"):
        await import_pilot_route(db_session, route)

    assert await db_session.scalar(select(func.count()).select_from(TransitStop)) == 0
    assert await db_session.scalar(select(func.count()).select_from(TransitRoute)) == 0


def _schedule_plan(
    route: PilotRoute,
    *,
    routable: bool = False,
    extra_stop_times: tuple[ScheduleTripStop, ...] = (),
) -> NormalizedSchedulePlan:
    provenance = {
        "source_file": "map.pdf",
        "source_page": "7",
        "effective_from": "2025-12-01",
        "effective_until": "",
        "source_last_updated": "",
        "freshness_as_of": "2026-09-12",
        "freshness_status": "unverified",
    }
    return NormalizedSchedulePlan(
        source_digest="digest-one",
        source_path="snapshot",
        effective_from=date(2025, 12, 1),
        effective_until=None,
        freshness_as_of=date(2026, 9, 12),
        freshness_status="unverified",
        routes=(
            ScheduleRouteInput(
                route=route,
                profiles=(
                    {
                        "basis": "timetable_header",
                        "service_start_local": "05:00",
                        "service_end_local": "21:00",
                        "service_end_alternate_local": "",
                        "headway_min_minutes": "25",
                        "headway_max_minutes": "55",
                        "headway_is_approximate": "true",
                        "fleet_count": "",
                        "notes": "",
                        **provenance,
                    },
                ),
                trips=(
                    ScheduleTripInput(
                        external_id="trip-1",
                        train_number=None,
                        service_class=None,
                        service_days=None,
                        is_estimated=True,
                        provenance=provenance,
                        stop_times=(
                            *(
                                ScheduleTripStop(
                                    sequence=stop.sequence,
                                    activity_id=stop.activity_id,
                                    scheduled_time_local=f"05:0{stop.sequence - 1}",
                                    day_offset=0,
                                    is_estimated=True,
                                )
                                for stop in route.stops
                            ),
                            *extra_stop_times,
                        ),
                    ),
                ),
                routable=routable,
            ),
        ),
        report={
            "attachable_routes": [route.route_id] if routable else [],
            "blocked_routes": [] if routable else [{"route_id": route.route_id}],
        },
    )


async def test_schedule_batch_is_idempotent_reversible_and_preserves_stop_raw(
    db_session,
) -> None:
    raw_rows = {
        "pilot-activity-a": {"description": "A", "medias": ["a.jpg"]},
        "pilot-activity-b": {"description": "B", "medias": ["b.jpg"]},
        "pilot-activity-schedule-only": {"description": "C", "medias": ["c.jpg"]},
    }
    for values in (
        {
            "external_id": external_id,
            "name": external_id,
            "mode": "bus",
            "operator": "TransJogja",
            "raw": raw,
            "source": "mapid_activities",
            "geom": func.ST_SetSRID(func.ST_MakePoint(110.3, -7.8), 4326),
        }
        for external_id, raw in raw_rows.items()
    ):
        await db_session.execute(insert(TransitStop).values(**values))
    await db_session.commit()
    route = PilotRoute(
        route_id="EV3",
        operator="TransJogja",
        mode="bus",
        headway_min=40,
        fare_idr=3500,
        source="normalized-transport:EV3;freshness_status=unverified",
        provenance={"freshness_status": "unverified"},
        stops=tuple(
            PilotStop(
                sequence=index,
                normalized_stop_id=f"stop-{index}",
                name=f"Stop {index}",
                activity_id=external_id,
                activity_name=f"Halte {index}",
                longitude=110.3,
                latitude=-7.8,
                activity_observed_at="2026-08-01T00:00:00Z",
                travel_time_from_prev_s=None if index == 1 else 180,
                match_status="matched_exact",
                review=None,
            )
            for index, external_id in enumerate(tuple(raw_rows)[:2], 1)
        ),
    )
    plan = _schedule_plan(
        route,
        extra_stop_times=(
            ScheduleTripStop(
                sequence=3,
                activity_id="pilot-activity-schedule-only",
                scheduled_time_local="05:02",
                day_offset=0,
                is_estimated=True,
            ),
        ),
    )
    import_key = f"test:{uuid4()}"

    first = await import_normalized_schedule(db_session, plan, import_key=import_key)
    second = await import_normalized_schedule(db_session, plan, import_key=import_key)

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert first["transit_stops_raw_unchanged"] is True
    assert await db_session.scalar(select(func.count()).select_from(TransitStop)) == 3
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(TransitScheduleImport)
            .where(TransitScheduleImport.import_key == import_key)
        )
        == 1
    )
    assert await db_session.scalar(select(func.count()).select_from(TransitServiceProfile)) == 1
    assert await db_session.scalar(select(func.count()).select_from(TransitTrip)) == 1
    assert await db_session.scalar(select(func.count()).select_from(TransitStopTime)) == 3
    assert await db_session.scalar(select(func.count()).select_from(RouteStop)) == 0
    assert first["routable_routes_imported"] == 0
    assert first["attached_stop_times"] == 3
    assert (
        dict((await db_session.execute(select(TransitStop.external_id, TransitStop.raw))).all())
        == raw_rows
    )

    rolled_back = await rollback_normalized_schedule(db_session, import_key)

    assert rolled_back["routes_removed"] == 1
    assert await db_session.scalar(select(func.count()).select_from(TransitRoute)) == 0
    assert await db_session.scalar(select(func.count()).select_from(TransitStop)) == 3
    assert (
        dict((await db_session.execute(select(TransitStop.external_id, TransitStop.raw))).all())
        == raw_rows
    )


def test_real_snapshot_reports_all_services_without_bridging_unresolved_stops() -> None:
    repository_root = Path(__file__).parents[3]
    plan = build_normalized_schedule_plan(
        repository_root / "transportation-data" / "normalized",
        review_paths=(
            repository_root / "transportation-data" / "review" / "ev3_stop_match_review.v2.csv",
        ),
    )

    assert plan.report["bus_routes_total"] == 20
    assert plan.report["rail_services_total"] == 6
    assert plan.report["blocked_route_count"] == 26
    assert plan.report["attachable_route_count"] == 0
    assert plan.report["route_records_total"] == 26
    assert plan.report["partial_route_count"] == 26
    assert plan.report["attached_stop_times"] > 0
    ev3 = next(row for row in plan.report["blocked_routes"] if row["route_id"] == "EV3")
    assert any("unmatched" in reason for reason in ev3["reasons"])

    ev3_route = next(item for item in plan.routes if item.route.route_id == "EV3")
    attached_activity_ids = {
        stop.activity_id for trip in ev3_route.trips for stop in trip.stop_times
    }
    assert "6a86caf989acf23707a36360" in attached_activity_ids
    assert "6a88263dd57440d48a1f481b" in attached_activity_ids
