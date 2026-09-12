"""Build and import one reviewed transport route from normalized snapshots.

Coordinates are never inferred. A stop must either have an exact Activity
match from extraction or an explicitly approved Activity review row.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.schema import (
    RouteStop,
    TransitRoute,
    TransitScheduleImport,
    TransitScheduleRoute,
    TransitServiceProfile,
    TransitStop,
    TransitStopTime,
    TransitTrip,
)

REVIEW_FIELDS = (
    "route_id",
    "stop_sequence",
    "stop_id",
    "stop_name",
    "match_status",
    "candidate_activity_id",
    "candidate_name",
    "score",
    "decision",
    "reviewer",
    "reviewed_at",
    "notes",
)

PROVENANCE_FIELDS = (
    "source_file",
    "source_page",
    "effective_from",
    "effective_until",
    "source_last_updated",
    "freshness_as_of",
    "freshness_status",
)


class PilotValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PilotStop:
    sequence: int
    normalized_stop_id: str
    name: str
    activity_id: str
    activity_name: str
    longitude: float
    latitude: float
    activity_observed_at: str
    travel_time_from_prev_s: int | None
    match_status: str
    review: dict[str, str] | None


@dataclass(frozen=True)
class PilotRoute:
    route_id: str
    operator: str
    mode: str
    headway_min: float
    fare_idr: int
    source: str
    provenance: dict[str, str]
    stops: tuple[PilotStop, ...]
    skipped_stop_sequences: tuple[int, ...] = ()


@dataclass(frozen=True)
class ScheduleTripStop:
    sequence: int
    activity_id: str
    scheduled_time_local: str
    day_offset: int
    is_estimated: bool


@dataclass(frozen=True)
class ScheduleTripInput:
    external_id: str
    train_number: str | None
    service_class: str | None
    service_days: str | None
    is_estimated: bool
    provenance: dict[str, str]
    stop_times: tuple[ScheduleTripStop, ...]


@dataclass(frozen=True)
class ScheduleRouteInput:
    route: PilotRoute
    profiles: tuple[dict[str, str], ...]
    trips: tuple[ScheduleTripInput, ...]
    routable: bool = True


@dataclass(frozen=True)
class NormalizedSchedulePlan:
    source_digest: str
    source_path: str
    effective_from: date | None
    effective_until: date | None
    freshness_as_of: date | None
    freshness_status: str
    routes: tuple[ScheduleRouteInput, ...]
    report: dict[str, object]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise PilotValidationError(f"missing normalized input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _route_stop_sequence(snapshot_dir: Path, route_id: str) -> list[dict[str, str]]:
    rows = [
        row for row in _read_csv(snapshot_dir / "bus_stop_times.csv") if row["route_id"] == route_id
    ]
    if not rows:
        raise PilotValidationError(f"route {route_id!r} has no bus timetable")

    by_sequence: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_sequence.setdefault(int(row["stop_sequence"]), []).append(row)
    sequence = []
    for number, occurrences in sorted(by_sequence.items()):
        stop_ids = {row["stop_id"] for row in occurrences}
        stop_names = {row["stop_name_raw"] for row in occurrences}
        if len(stop_ids) != 1 or len(stop_names) != 1:
            raise PilotValidationError(
                f"route {route_id} stop sequence {number} changes between trips"
            )
        sequence.append(occurrences[0])
    numbers = [int(row["stop_sequence"]) for row in sequence]
    if numbers != list(range(1, len(numbers) + 1)):
        raise PilotValidationError(f"route {route_id} stop sequence is not contiguous")
    return sequence


def write_stop_review_template(snapshot_dir: Path, route_id: str, output_path: Path) -> int:
    """Write candidate review sheet once; never overwrite human decisions."""
    sequence = _route_stop_sequence(snapshot_dir, route_id)
    stops = {row["stop_id"]: row for row in _read_csv(snapshot_dir / "stops.csv")}
    candidates: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(snapshot_dir / "stop_match_candidates.csv"):
        candidates.setdefault(row["stop_id"], []).append(row)

    rows: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for route_stop in sequence:
        stop_id = route_stop["stop_id"]
        if stop_id in seen:
            continue
        seen.add(stop_id)
        stop = stops[stop_id]
        if stop["match_status"] == "matched_exact":
            continue
        options = candidates.get(stop_id) or [{}]
        for candidate in options:
            rows.append(
                {
                    "route_id": route_id,
                    "stop_sequence": route_stop["stop_sequence"],
                    "stop_id": stop_id,
                    "stop_name": route_stop["stop_name_raw"],
                    "match_status": stop["match_status"],
                    "candidate_activity_id": candidate.get("candidate_activity_id", ""),
                    "candidate_name": candidate.get("candidate_name", ""),
                    "score": candidate.get("score", ""),
                    "decision": "",
                    "reviewer": "",
                    "reviewed_at": "",
                    "notes": "",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, REVIEW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _approved_reviews(path: Path | None, route_id: str) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    approved: dict[str, dict[str, str]] = {}
    for row in _read_csv(path):
        if row.get("route_id") != route_id or row.get("decision", "").casefold() != "approved":
            continue
        missing_audit = [field for field in ("reviewer", "reviewed_at") if not row.get(field)]
        if missing_audit:
            raise PilotValidationError(
                f"approved review for {row.get('stop_id')} lacks {', '.join(missing_audit)}"
            )
        stop_id = row.get("stop_id", "")
        activity_id = row.get("candidate_activity_id", "")
        if not stop_id or not activity_id:
            raise PilotValidationError("approved review lacks stop_id or candidate_activity_id")
        if stop_id in approved:
            raise PilotValidationError(f"multiple approved Activity matches for {stop_id}")
        approved[stop_id] = row
    return approved


def load_pilot_route(
    snapshot_dir: Path,
    *,
    route_id: str = "EV3",
    reviews_path: Path | None = None,
    skip_stop_sequences: set[int] | None = None,
    skip_reason: str = "",
) -> PilotRoute:
    sequence = _route_stop_sequence(snapshot_dir, route_id)
    skipped = set(skip_stop_sequences or ())
    sequence_numbers = {int(row["stop_sequence"]) for row in sequence}
    unknown_skips = sorted(skipped - sequence_numbers)
    if unknown_skips:
        raise PilotValidationError(
            f"skip positions are outside route {route_id}: " + ", ".join(map(str, unknown_skips))
        )
    if skipped and not skip_reason.strip():
        raise PilotValidationError("skip_reason is required when omitting route stops")
    stops = {row["stop_id"]: row for row in _read_csv(snapshot_dir / "stops.csv")}
    activities = {
        row["source_id"]: row for row in _read_csv(snapshot_dir / "activity_stop_catalog.csv")
    }
    reviews = _approved_reviews(reviews_path, route_id)
    route_stop_ids = {row["stop_id"] for row in sequence}
    unknown_review_stops = sorted(set(reviews) - route_stop_ids)
    if unknown_review_stops:
        raise PilotValidationError(
            f"approved reviews reference stops outside route {route_id}: "
            + ", ".join(unknown_review_stops)
        )

    profiles = [
        row
        for row in _read_csv(snapshot_dir / "service_profiles.csv")
        if row["route_id"] == route_id and row["basis"] == "timetable_header"
    ]
    if len(profiles) != 1:
        raise PilotValidationError(
            f"route {route_id} needs exactly one timetable_header service profile"
        )
    profile = profiles[0]
    headway_min = (
        float(profile["headway_min_minutes"]) + float(profile["headway_max_minutes"])
    ) / 2

    cash_fares = [
        row
        for row in _read_csv(snapshot_dir / "fares.csv")
        if row["service_id"] == "transjogja" and row["payment_method"] == "cash"
    ]
    if len(cash_fares) != 1 or cash_fares[0]["fare_min"] != cash_fares[0]["fare_max"]:
        raise PilotValidationError("TransJogja cash fare must be one fixed value")

    segments = {
        int(row["to_stop_sequence"]): row
        for row in _read_csv(snapshot_dir / "bus_segments.csv")
        if row["route_id"] == route_id
    }
    unresolved: list[str] = []
    pilot_stops: list[PilotStop] = []
    sequence_stop_ids = {int(row["stop_sequence"]): row["stop_id"] for row in sequence}
    last_included_sequence: int | None = None
    for route_stop in sequence:
        number = int(route_stop["stop_sequence"])
        stop_id = route_stop["stop_id"]
        stop = stops.get(stop_id)
        if stop is None:
            raise PilotValidationError(f"stop {stop_id} absent from stops.csv")

        review = reviews.get(stop_id)
        if stop["match_status"] == "matched_exact":
            if review is not None:
                raise PilotValidationError(f"exact stop {stop_id} must not have an override")
            activity_id = stop["matched_activity_id"]
            activity = activities.get(activity_id)
            match_status = "matched_exact"
        elif review is not None:
            activity_id = review["candidate_activity_id"]
            activity = activities.get(activity_id)
            match_status = "reviewed_activity"
        else:
            activity_id = ""
            activity = None
            match_status = ""
        if number in skipped:
            if activity is not None:
                raise PilotValidationError(
                    f"refusing to skip resolved stop {number}:{route_stop['stop_name_raw']}"
                )
            continue
        if activity is None:
            if activity_id:
                raise PilotValidationError(
                    f"Activity {activity_id!r} for stop {stop_id} absent from catalog"
                )
            unresolved.append(f"{number}:{route_stop['stop_name_raw']} [{stop['match_status']}]")
            continue
        try:
            longitude = float(activity["longitude"])
            latitude = float(activity["latitude"])
        except (KeyError, TypeError, ValueError) as error:
            raise PilotValidationError(
                f"Activity {activity_id!r} has invalid coordinates"
            ) from error
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise PilotValidationError(
                f"Activity {activity_id!r} coordinates are outside WGS84 bounds"
            )

        if last_included_sequence is None:
            travel_time = None
        else:
            travel_time = 0
            for to_sequence in range(last_included_sequence + 1, number + 1):
                segment = segments.get(to_sequence)
                if (
                    segment is None
                    or int(segment["from_stop_sequence"]) != to_sequence - 1
                    or segment["from_stop_id"] != sequence_stop_ids[to_sequence - 1]
                    or segment["to_stop_id"] != sequence_stop_ids[to_sequence]
                ):
                    raise PilotValidationError(
                        f"route {route_id} lacks valid adjacent segment ending at "
                        f"sequence {to_sequence}"
                    )
                travel_time += int(segment["travel_time_s"])

        pilot_stops.append(
            PilotStop(
                sequence=number,
                normalized_stop_id=stop_id,
                name=route_stop["stop_name_raw"],
                activity_id=activity_id,
                activity_name=activity["name"],
                longitude=longitude,
                latitude=latitude,
                activity_observed_at=activity["observed_at"],
                travel_time_from_prev_s=travel_time,
                match_status=match_status,
                review=review,
            )
        )
        last_included_sequence = number

    if unresolved:
        detail = "; ".join(unresolved)
        raise PilotValidationError(
            f"route {route_id} has {len(unresolved)} unresolved stop positions: {detail}"
        )

    provenance = {
        field: profile[field]
        for field in (
            "source_file",
            "source_page",
            "effective_from",
            "effective_until",
            "source_last_updated",
            "freshness_as_of",
            "freshness_status",
        )
    }
    if skipped:
        provenance["skipped_stop_sequences"] = ",".join(map(str, sorted(skipped)))
        provenance["skip_reason"] = skip_reason.strip()
    source = (
        "transport-pdf:"
        + route_id
        + ";"
        + ";".join(f"{key}={value}" for key, value in provenance.items() if value)
    )
    return PilotRoute(
        route_id=route_id,
        operator="TransJogja",
        mode="bus",
        headway_min=headway_min,
        fare_idr=int(cash_fares[0]["fare_min"]),
        source=source,
        provenance=provenance,
        stops=tuple(pilot_stops),
        skipped_stop_sequences=tuple(sorted(skipped)),
    )


def _provenance(row: dict[str, str]) -> dict[str, str]:
    return {field: row.get(field, "") for field in PROVENANCE_FIELDS}


def _optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _as_bool(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes"}


def _snapshot_digest(snapshot_dir: Path, review_paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    names = (
        "stops.csv",
        "activity_stop_catalog.csv",
        "routes.csv",
        "route_stops.csv",
        "service_profiles.csv",
        "fares.csv",
        "bus_segments.csv",
        "bus_trips.csv",
        "bus_stop_times.csv",
        "rail_services.csv",
        "rail_trips.csv",
        "rail_stop_times.csv",
    )
    for path in (*(snapshot_dir / name for name in names), *review_paths):
        if not path.is_file():
            raise PilotValidationError(f"missing normalized input: {path}")
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _combined_reviews(paths: tuple[Path, ...]) -> dict[tuple[str, str], dict[str, str]]:
    approved: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        for row in _read_csv(path):
            if row.get("decision", "").casefold() != "approved":
                continue
            missing = [
                field
                for field in (
                    "route_id",
                    "stop_id",
                    "candidate_activity_id",
                    "reviewer",
                    "reviewed_at",
                )
                if not row.get(field)
            ]
            if missing:
                raise PilotValidationError(f"approved review in {path} lacks {', '.join(missing)}")
            key = (row["route_id"], row["stop_id"])
            previous = approved.get(key)
            if previous and previous["candidate_activity_id"] != row["candidate_activity_id"]:
                raise PilotValidationError(
                    f"conflicting approved Activity matches for {row['route_id']}:{row['stop_id']}"
                )
            approved[key] = row
    return approved


def _minutes(time_local: str, day_offset: str | int = 0) -> int:
    try:
        hour, minute = (int(part) for part in time_local.split(":"))
        return int(day_offset) * 24 * 60 + hour * 60 + minute
    except (TypeError, ValueError) as error:
        raise PilotValidationError(f"invalid local schedule time {time_local!r}") from error


def build_normalized_schedule_plan(
    snapshot_dir: Path, *, review_paths: tuple[Path, ...] = ()
) -> NormalizedSchedulePlan:
    """Validate every normalized service and keep only complete Activity-backed routes."""
    stops = {row["stop_id"]: row for row in _read_csv(snapshot_dir / "stops.csv")}
    activities = {
        row["source_id"]: row for row in _read_csv(snapshot_dir / "activity_stop_catalog.csv")
    }
    reviews = _combined_reviews(review_paths)
    profiles = _read_csv(snapshot_dir / "service_profiles.csv")
    fares = _read_csv(snapshot_dir / "fares.csv")
    bus_segments = _read_csv(snapshot_dir / "bus_segments.csv")
    bus_trips = _read_csv(snapshot_dir / "bus_trips.csv")
    bus_times = _read_csv(snapshot_dir / "bus_stop_times.csv")
    rail_trips = _read_csv(snapshot_dir / "rail_trips.csv")
    rail_times = _read_csv(snapshot_dir / "rail_stop_times.csv")

    report: dict[str, object] = {
        "activity_catalog_total": len(activities),
        "normalized_stops_total": len(stops),
        "bus_routes_total": 0,
        "rail_services_total": 0,
        "attachable_routes": [],
        "blocked_routes": [],
    }
    output: list[ScheduleRouteInput] = []

    def resolve(route_id: str, source_stop_id: str) -> tuple[str, str]:
        stop = stops.get(source_stop_id)
        if stop is None:
            return "", "missing_stop_row"
        if stop.get("match_status") == "matched_exact" and stop.get("matched_activity_id"):
            activity_id = stop["matched_activity_id"]
            return (
                (activity_id, "matched_exact")
                if activity_id in activities
                else ("", "missing_activity")
            )
        review = reviews.get((route_id, source_stop_id))
        if review:
            activity_id = review["candidate_activity_id"]
            return (
                (activity_id, "reviewed_activity")
                if activity_id in activities
                else ("", "missing_activity")
            )
        return "", stop.get("match_status") or "unmatched"

    def fixed_fare(service_id: str) -> int | None:
        matches = [
            row
            for row in fares
            if row["service_id"] == service_id
            and row.get("fare_min")
            and row["fare_min"] == row.get("fare_max")
        ]
        values = {int(row["fare_min"]) for row in matches}
        return values.pop() if len(values) == 1 else None

    bus_route_rows = _read_csv(snapshot_dir / "routes.csv")
    bus_path_rows = _read_csv(snapshot_dir / "route_stops.csv")
    report["bus_routes_total"] = len(bus_route_rows)
    for metadata in bus_route_rows:
        route_id = metadata["route_id"]
        path_rows = sorted(
            (row for row in bus_path_rows if row["route_id"] == route_id),
            key=lambda row: int(row["stop_sequence"]),
        )
        numbers = [int(row["stop_sequence"]) for row in path_rows]
        reasons: list[str] = []
        if not numbers or numbers != list(range(1, len(numbers) + 1)):
            reasons.append("non_contiguous_path")
        resolved: list[tuple[dict[str, str], str, str]] = []
        for row in path_rows:
            activity_id, status = resolve(route_id, row["stop_id"])
            if not activity_id:
                reasons.append(f"{row['stop_id']}:{status}")
            else:
                resolved.append((row, activity_id, status))

        route_profiles = tuple(row for row in profiles if row["route_id"] == route_id)
        preferred = next(
            (row for row in route_profiles if row["basis"] == "map_nominal"),
            next((row for row in route_profiles if row["basis"] == "timetable_header"), None),
        )
        if preferred is None or not preferred.get("headway_min_minutes"):
            reasons.append("missing_headway")
        fare = fixed_fare("transjogja")
        if fare is None:
            reasons.append("non_fixed_fare")

        detailed = any(row["route_id"] == route_id for row in bus_trips)
        segment_by_to = {
            int(row["to_stop_sequence"]): row for row in bus_segments if row["route_id"] == route_id
        }
        if detailed:
            for number in numbers[1:]:
                segment = segment_by_to.get(number)
                if not segment or int(segment["from_stop_sequence"]) != number - 1:
                    reasons.append(f"missing_segment:{number - 1}-{number}")

        if reasons:
            report["blocked_routes"].append(
                {"route_id": route_id, "mode": "bus", "reasons": sorted(set(reasons))}
            )
        else:
            report["attachable_routes"].append(route_id)
        routable = not reasons

        pilot_stops = []
        activity_by_source_stop: dict[str, str] = {}
        for row, activity_id, status in resolved:
            number = int(row["stop_sequence"])
            activity = activities[activity_id]
            activity_by_source_stop[row["stop_id"]] = activity_id
            pilot_stops.append(
                PilotStop(
                    sequence=number,
                    normalized_stop_id=row["stop_id"],
                    name=row["stop_name_raw"],
                    activity_id=activity_id,
                    activity_name=activity["name"],
                    longitude=float(activity["longitude"]),
                    latitude=float(activity["latitude"]),
                    activity_observed_at=activity["observed_at"],
                    travel_time_from_prev_s=(
                        int(segment_by_to[number]["travel_time_s"])
                        if number in segment_by_to
                        else None
                    ),
                    match_status=status,
                    review=reviews.get((route_id, row["stop_id"])),
                )
            )
        trip_inputs: list[ScheduleTripInput] = []
        for trip in (row for row in bus_trips if row["route_id"] == route_id):
            rows = sorted(
                (row for row in bus_times if row["trip_id"] == trip["trip_id"]),
                key=lambda row: int(row["stop_sequence"]),
            )
            stop_times = tuple(
                ScheduleTripStop(
                    sequence=int(row["stop_sequence"]),
                    activity_id=activity_by_source_stop[row["stop_id"]],
                    scheduled_time_local=row["scheduled_time_local"],
                    day_offset=int(row["day_offset"] or 0),
                    is_estimated=_as_bool(row.get("is_estimated", "")),
                )
                for row in rows
                if row["stop_id"] in activity_by_source_stop
            )
            if not stop_times:
                continue
            trip_inputs.append(
                ScheduleTripInput(
                    external_id=trip["trip_id"],
                    train_number=None,
                    service_class=None,
                    service_days=None,
                    is_estimated=_as_bool(trip.get("is_estimated", "")),
                    provenance=_provenance(trip),
                    stop_times=stop_times,
                )
            )
        provenance = _provenance(metadata)
        output.append(
            ScheduleRouteInput(
                route=PilotRoute(
                    route_id=route_id,
                    operator=metadata["operator"],
                    mode=metadata["mode"],
                    headway_min=(
                        (
                            float(preferred["headway_min_minutes"])
                            + float(
                                preferred.get("headway_max_minutes")
                                or preferred["headway_min_minutes"]
                            )
                        )
                        / 2
                        if preferred is not None and preferred.get("headway_min_minutes")
                        else 0
                    ),
                    fare_idr=fare or 0,
                    source="normalized-transport:"
                    + route_id
                    + f";routable={str(routable).lower()};"
                    + ";".join(f"{key}={value}" for key, value in provenance.items() if value),
                    provenance=provenance,
                    stops=tuple(pilot_stops),
                ),
                profiles=route_profiles,
                trips=tuple(trip_inputs),
                routable=routable,
            )
        )

    rail_service_rows = _read_csv(snapshot_dir / "rail_services.csv")
    report["rail_services_total"] = len(rail_service_rows)
    for metadata in rail_service_rows:
        route_id = metadata["service_id"]
        service_trips = [row for row in rail_trips if row["service_id"] == route_id]
        trip_time_rows = {
            trip["trip_id"]: sorted(
                (row for row in rail_times if row["trip_id"] == trip["trip_id"]),
                key=lambda row: int(row["stop_sequence"]),
            )
            for trip in service_trips
        }
        reasons: list[str] = []
        patterns = {tuple(row["stop_id"] for row in rows) for rows in trip_time_rows.values()}
        if not patterns or len(patterns) != 1:
            reasons.append("inconsistent_trip_stop_pattern")
        resolved_ids: dict[str, tuple[str, str]] = {}
        all_source_stop_ids = {row["stop_id"] for rows in trip_time_rows.values() for row in rows}
        for source_stop_id in all_source_stop_ids:
            activity_id, status = resolve(route_id, source_stop_id)
            if not activity_id:
                reasons.append(f"{source_stop_id}:{status}")
            else:
                resolved_ids[source_stop_id] = (activity_id, status)

        fare_key = (
            "krl"
            if route_id.startswith("krl_")
            else "yia"
            if route_id.startswith("yia_")
            else "prameks"
        )
        fare = fixed_fare(fare_key)
        if fare is None:
            reasons.append("non_fixed_fare")
        departures = sorted(
            _minutes(rows[0]["scheduled_time_local"], rows[0].get("day_offset", "0"))
            for rows in trip_time_rows.values()
            if rows
        )
        gaps = [
            right - left
            for left, right in zip(departures, departures[1:], strict=False)
            if right > left
        ]
        if not gaps:
            reasons.append("insufficient_departures_for_headway")
        if reasons:
            report["blocked_routes"].append(
                {
                    "route_id": route_id,
                    "mode": metadata["mode"],
                    "reasons": sorted(set(reasons)),
                }
            )
        else:
            report["attachable_routes"].append(route_id)
        routable = not reasons

        first_rows = max(trip_time_rows.values(), key=len, default=[])
        pilot_stops: list[PilotStop] = []
        for index, row in enumerate(first_rows):
            resolved = resolved_ids.get(row["stop_id"])
            if resolved is None:
                continue
            activity_id, status = resolved
            activity = activities[activity_id]
            previous = first_rows[index - 1] if index else None
            travel_time = (
                (
                    _minutes(row["scheduled_time_local"], row.get("day_offset", "0"))
                    - _minutes(previous["scheduled_time_local"], previous.get("day_offset", "0"))
                )
                * 60
                if previous and previous["stop_id"] in resolved_ids
                else None
            )
            if travel_time is not None and travel_time <= 0:
                raise PilotValidationError(f"rail service {route_id} has non-positive segment time")
            pilot_stops.append(
                PilotStop(
                    sequence=index + 1,
                    normalized_stop_id=row["stop_id"],
                    name=row["station_name_raw"],
                    activity_id=activity_id,
                    activity_name=activity["name"],
                    longitude=float(activity["longitude"]),
                    latitude=float(activity["latitude"]),
                    activity_observed_at=activity["observed_at"],
                    travel_time_from_prev_s=travel_time,
                    match_status=status,
                    review=reviews.get((route_id, row["stop_id"])),
                )
            )
        trip_input_list: list[ScheduleTripInput] = []
        for trip in service_trips:
            stop_times = tuple(
                ScheduleTripStop(
                    sequence=int(row["stop_sequence"]),
                    activity_id=resolved_ids[row["stop_id"]][0],
                    scheduled_time_local=row["scheduled_time_local"],
                    day_offset=int(row["day_offset"] or 0),
                    is_estimated=False,
                )
                for row in trip_time_rows[trip["trip_id"]]
                if row["stop_id"] in resolved_ids
            )
            if not stop_times:
                continue
            trip_input_list.append(
                ScheduleTripInput(
                    external_id=trip["trip_id"],
                    train_number=trip.get("train_number") or None,
                    service_class=trip.get("service_class") or None,
                    service_days=trip.get("service_days") or None,
                    is_estimated=False,
                    provenance=_provenance(trip),
                    stop_times=stop_times,
                )
            )
        provenance = _provenance(metadata)
        rail_profile = {
            "route_id": route_id,
            "basis": "derived_timetable",
            "service_start_local": (
                min(rows[0]["scheduled_time_local"] for rows in trip_time_rows.values() if rows)
                if departures
                else ""
            ),
            "service_end_local": (
                max(rows[-1]["scheduled_time_local"] for rows in trip_time_rows.values() if rows)
                if departures
                else ""
            ),
            "service_end_alternate_local": "",
            "headway_min_minutes": str(min(gaps)) if gaps else "",
            "headway_max_minutes": str(max(gaps)) if gaps else "",
            "headway_is_approximate": "true",
            "fleet_count": "",
            "notes": "Derived from published departures; freshness remains unverified.",
            **provenance,
        }
        output.append(
            ScheduleRouteInput(
                route=PilotRoute(
                    route_id=route_id,
                    operator=metadata["operator"],
                    mode=metadata["mode"],
                    headway_min=float(statistics.median(gaps)) if gaps else 0,
                    fare_idr=fare or 0,
                    source="normalized-transport:"
                    + route_id
                    + f";routable={str(routable).lower()};"
                    + ";".join(f"{key}={value}" for key, value in provenance.items() if value),
                    provenance=provenance,
                    stops=tuple(pilot_stops),
                ),
                profiles=(rail_profile,),
                trips=tuple(trip_input_list),
                routable=routable,
            )
        )

    all_provenance = [item.route.provenance for item in output]
    effective_from_values = sorted(
        value for row in all_provenance if (value := row.get("effective_from"))
    )
    effective_until_values = sorted(
        value for row in all_provenance if (value := row.get("effective_until"))
    )
    freshness_values = sorted(
        value for row in all_provenance if (value := row.get("freshness_as_of"))
    )
    freshness_statuses = {row.get("freshness_status", "unverified") for row in all_provenance}
    report["route_records_total"] = len(output)
    report["attachable_route_count"] = len(report["attachable_routes"])
    report["partial_route_count"] = sum(not item.routable for item in output)
    report["blocked_route_count"] = len(report["blocked_routes"])
    report["blocked_routable_routes"] = [row["route_id"] for row in report["blocked_routes"]]
    report["trip_count"] = sum(len(item.trips) for item in output)
    report["attached_stop_times"] = sum(
        len(trip.stop_times) for item in output for trip in item.trips
    )
    report["stop_time_count"] = report["attached_stop_times"]
    return NormalizedSchedulePlan(
        source_digest=_snapshot_digest(snapshot_dir, review_paths),
        source_path=str(snapshot_dir),
        effective_from=_optional_date(effective_from_values[0]) if effective_from_values else None,
        effective_until=(
            _optional_date(effective_until_values[-1]) if effective_until_values else None
        ),
        freshness_as_of=_optional_date(freshness_values[-1]) if freshness_values else None,
        freshness_status=("verified" if freshness_statuses == {"verified"} else "unverified"),
        routes=tuple(output),
        report=report,
    )


async def import_pilot_route(session: AsyncSession, route: PilotRoute) -> dict[str, int]:
    """Attach one route to pre-ingested Activity stops; never create or edit stops."""
    stop_database_ids: dict[int, int] = {}
    missing_activity_ids: list[str] = []
    for stop in route.stops:
        database_id = await session.scalar(
            select(TransitStop.id).where(TransitStop.external_id == stop.activity_id)
        )
        if database_id is None:
            missing_activity_ids.append(stop.activity_id)
            continue
        stop_database_ids[stop.sequence] = database_id

    if missing_activity_ids:
        raise PilotValidationError(
            "route "
            f"{route.route_id} references {len(missing_activity_ids)} Activity stops "
            "not ingested into transit_stops: " + ", ".join(sorted(set(missing_activity_ids)))
        )

    route_rows = (
        await session.scalars(
            select(TransitRoute).where(
                TransitRoute.name == route.route_id,
                TransitRoute.operator == route.operator,
                TransitRoute.mode == route.mode,
                TransitRoute.source.like(f"transport-pdf:{route.route_id};%"),
            )
        )
    ).all()
    if len(route_rows) > 1:
        raise PilotValidationError(f"multiple source-owned routes found for {route.route_id}")
    if route_rows:
        database_route = route_rows[0]
        database_route.headway_min = route.headway_min
        database_route.fare_idr = route.fare_idr
        database_route.source = route.source
        database_route.updated_at = func.now()
    else:
        database_route = TransitRoute(
            name=route.route_id,
            operator=route.operator,
            mode=route.mode,
            headway_min=route.headway_min,
            fare_idr=route.fare_idr,
            source=route.source,
        )
        session.add(database_route)
    await session.flush()

    route_stop_rows = [
        {
            "route_id": database_route.id,
            "stop_id": stop_database_ids[stop.sequence],
            "seq": stop.sequence - 1,
            "travel_time_from_prev_s": stop.travel_time_from_prev_s,
        }
        for stop in route.stops
    ]
    statement = pg_insert(RouteStop).values(route_stop_rows)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[RouteStop.route_id, RouteStop.seq],
            set_={
                "stop_id": statement.excluded.stop_id,
                "travel_time_from_prev_s": statement.excluded.travel_time_from_prev_s,
            },
        )
    )
    sequences = [row["seq"] for row in route_stop_rows]
    await session.execute(
        delete(RouteStop).where(
            RouteStop.route_id == database_route.id,
            RouteStop.seq.not_in(sequences),
        )
    )
    await session.commit()
    return {
        "route_id": database_route.id,
        "stops": len(set(stop_database_ids.values())),
        "route_stops": len(route_stop_rows),
    }


async def _stop_fingerprint(session: AsyncSession) -> tuple[int, str]:
    rows = (
        await session.execute(
            select(TransitStop.id, TransitStop.external_id, TransitStop.raw).order_by(
                TransitStop.id
            )
        )
    ).all()
    encoded = json.dumps(
        [(row.id, row.external_id, row.raw) for row in rows],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return len(rows), hashlib.sha256(encoded).hexdigest()


async def dry_run_normalized_schedule(
    session: AsyncSession, plan: NormalizedSchedulePlan
) -> dict[str, object]:
    """Check canonical Activity coverage without writing database state."""
    report = json.loads(json.dumps(plan.report))
    external_ids = {stop.activity_id for item in plan.routes for stop in item.route.stops}
    existing = (
        set(
            await session.scalars(
                select(TransitStop.external_id).where(TransitStop.external_id.in_(external_ids))
            )
        )
        if external_ids
        else set()
    )
    database_blocked: list[dict[str, object]] = []
    database_routable: list[str] = []
    database_schedule_routes: list[str] = []
    for item in plan.routes:
        database_schedule_routes.append(item.route.route_id)
        missing = sorted({stop.activity_id for stop in item.route.stops} - existing)
        if missing:
            database_blocked.append(
                {
                    "route_id": item.route.route_id,
                    "reason": "activity_not_ingested",
                    "activity_ids": missing,
                }
            )
        elif item.routable:
            database_routable.append(item.route.route_id)
    database_stop_times = sum(
        stop_time.activity_id in existing
        for item in plan.routes
        for trip in item.trips
        for stop_time in trip.stop_times
    )
    count, raw_digest = await _stop_fingerprint(session)
    report.update(
        {
            "database_activity_stop_count": count,
            "database_activity_raw_digest": raw_digest,
            "database_schedule_routes": database_schedule_routes,
            "database_routable_routes": database_routable,
            "database_attached_stop_times": database_stop_times,
            "database_blocked_routes": database_blocked,
            "would_write": False,
        }
    )
    return report


async def import_normalized_schedule(
    session: AsyncSession,
    plan: NormalizedSchedulePlan,
    *,
    import_key: str | None = None,
) -> dict[str, object]:
    """Atomically enrich surveyed stops; only complete routes gain adjacency."""
    key = import_key or f"normalized:{plan.source_digest}"
    previous = await session.scalar(
        select(TransitScheduleImport).where(TransitScheduleImport.import_key == key)
    )
    if previous is not None and previous.status == "complete":
        return {
            "schedule_import_id": previous.id,
            "idempotent": True,
            **previous.report,
        }
    if previous is not None and previous.status != "rolled_back":
        raise PilotValidationError(
            f"schedule import {key!r} exists with status {previous.status!r}"
        )

    before_count, before_raw_digest = await _stop_fingerprint(session)
    dry_run = await dry_run_normalized_schedule(session, plan)
    route_inputs = list(plan.routes)
    stop_ids = {stop.activity_id for item in route_inputs for stop in item.route.stops}
    stop_database_ids = (
        dict(
            (
                await session.execute(
                    select(TransitStop.external_id, TransitStop.id).where(
                        TransitStop.external_id.in_(stop_ids)
                    )
                )
            ).all()
        )
        if stop_ids
        else {}
    )

    if previous is None:
        batch = TransitScheduleImport(
            import_key=key,
            source_digest=plan.source_digest,
            source_path=plan.source_path,
            status="applying",
            effective_from=plan.effective_from,
            effective_until=plan.effective_until,
            freshness_as_of=plan.freshness_as_of,
            freshness_status=plan.freshness_status,
            report={},
        )
        session.add(batch)
    else:
        batch = previous
        await session.execute(
            delete(TransitScheduleRoute).where(TransitScheduleRoute.schedule_import_id == batch.id)
        )
        batch.status = "applying"
        batch.report = {}
    await session.flush()

    backups: dict[str, object] = {}
    imported_trip_count = 0
    imported_stop_time_count = 0
    try:
        for item in route_inputs:
            route = item.route
            route_activity_ids = {stop.activity_id for stop in route.stops}
            database_routable = item.routable and route_activity_ids <= stop_database_ids.keys()
            matches = (
                await session.scalars(
                    select(TransitRoute).where(
                        TransitRoute.name == route.route_id,
                        TransitRoute.operator == route.operator,
                        TransitRoute.mode == route.mode,
                    )
                )
            ).all()
            if len(matches) > 1:
                raise PilotValidationError(
                    f"multiple routes found for {route.route_id}/{route.operator}/{route.mode}"
                )
            created_route = not matches
            if created_route:
                database_route = TransitRoute(
                    name=route.route_id,
                    operator=route.operator,
                    mode=route.mode,
                    headway_min=route.headway_min,
                    fare_idr=route.fare_idr,
                    source=route.source.replace(
                        "routable=true", f"routable={str(database_routable).lower()}"
                    ),
                )
                session.add(database_route)
                await session.flush()
            else:
                database_route = matches[0]
                old_path = (
                    await session.execute(
                        select(
                            RouteStop.seq,
                            RouteStop.stop_id,
                            RouteStop.travel_time_from_prev_s,
                        )
                        .where(RouteStop.route_id == database_route.id)
                        .order_by(RouteStop.seq)
                    )
                ).all()
                backups[str(database_route.id)] = {
                    "headway_min": database_route.headway_min,
                    "fare_idr": database_route.fare_idr,
                    "source": database_route.source,
                    "route_stops": [list(row) for row in old_path],
                }
                # A partial schedule may enrich known stops, but it does not
                # own enough evidence to rewrite an already-routable path or
                # its route-level fare/headway metadata.
                if database_routable:
                    database_route.headway_min = route.headway_min
                    database_route.fare_idr = route.fare_idr
                    database_route.source = route.source
                    database_route.updated_at = func.now()

            session.add(
                TransitScheduleRoute(
                    schedule_import_id=batch.id,
                    route_id=database_route.id,
                    source_route_id=route.route_id,
                    created_route=created_route,
                )
            )
            if database_routable:
                await session.execute(
                    delete(RouteStop).where(RouteStop.route_id == database_route.id)
                )
                route_stop_rows = [
                    {
                        "route_id": database_route.id,
                        "stop_id": stop_database_ids[stop.activity_id],
                        "seq": stop.sequence - 1,
                        "travel_time_from_prev_s": stop.travel_time_from_prev_s,
                    }
                    for stop in route.stops
                ]
                if route_stop_rows:
                    await session.execute(pg_insert(RouteStop).values(route_stop_rows))

            for profile in item.profiles:
                session.add(
                    TransitServiceProfile(
                        schedule_import_id=batch.id,
                        route_id=database_route.id,
                        basis=profile["basis"],
                        service_start_local=profile.get("service_start_local") or None,
                        service_end_local=profile.get("service_end_local") or None,
                        service_end_alternate_local=(
                            profile.get("service_end_alternate_local") or None
                        ),
                        headway_min_minutes=(
                            float(profile["headway_min_minutes"])
                            if profile.get("headway_min_minutes")
                            else None
                        ),
                        headway_max_minutes=(
                            float(profile["headway_max_minutes"])
                            if profile.get("headway_max_minutes")
                            else None
                        ),
                        headway_is_approximate=_as_bool(profile.get("headway_is_approximate", "")),
                        fleet_count=(
                            int(profile["fleet_count"]) if profile.get("fleet_count") else None
                        ),
                        notes=profile.get("notes") or None,
                        provenance=_provenance(profile),
                    )
                )
            for trip in item.trips:
                attached_times = [
                    stop_time
                    for stop_time in trip.stop_times
                    if stop_time.activity_id in stop_database_ids
                ]
                if not attached_times:
                    continue
                database_trip = TransitTrip(
                    schedule_import_id=batch.id,
                    route_id=database_route.id,
                    external_id=trip.external_id,
                    train_number=trip.train_number,
                    service_class=trip.service_class,
                    service_days=trip.service_days,
                    is_estimated=trip.is_estimated,
                    provenance=trip.provenance,
                )
                session.add(database_trip)
                await session.flush()
                session.add_all(
                    [
                        TransitStopTime(
                            trip_id=database_trip.id,
                            stop_id=stop_database_ids[stop_time.activity_id],
                            seq=stop_time.sequence - 1,
                            scheduled_time_local=stop_time.scheduled_time_local,
                            day_offset=stop_time.day_offset,
                            is_estimated=stop_time.is_estimated,
                        )
                        for stop_time in attached_times
                    ]
                )
                imported_trip_count += 1
                imported_stop_time_count += len(attached_times)

        await session.flush()
        after_count, after_raw_digest = await _stop_fingerprint(session)
        if (after_count, after_raw_digest) != (before_count, before_raw_digest):
            raise RuntimeError("schedule import modified canonical transit_stops")
        result: dict[str, object] = {
            **dry_run,
            "would_write": True,
            "routes_imported": len(route_inputs),
            "routable_routes_imported": sum(
                item.routable
                and {stop.activity_id for stop in item.route.stops} <= stop_database_ids.keys()
                for item in route_inputs
            ),
            "profiles_imported": sum(len(item.profiles) for item in route_inputs),
            "trips_imported": imported_trip_count,
            "stop_times_imported": imported_stop_time_count,
            "attached_stop_times": imported_stop_time_count,
            "transit_stops_before": before_count,
            "transit_stops_after": after_count,
            "transit_stops_raw_unchanged": True,
            "route_backups": backups,
        }
        batch.report = result
        batch.status = "complete"
        await session.commit()
        return {"schedule_import_id": batch.id, "idempotent": False, **result}
    except Exception:
        await session.rollback()
        raise


async def rollback_normalized_schedule(session: AsyncSession, import_key: str) -> dict[str, int]:
    """Remove one imported batch while preserving every canonical Activity stop."""
    batch = await session.scalar(
        select(TransitScheduleImport).where(TransitScheduleImport.import_key == import_key)
    )
    if batch is None:
        raise PilotValidationError(f"schedule import {import_key!r} does not exist")
    if batch.status == "rolled_back":
        return {"schedule_import_id": batch.id, "routes_removed": 0, "routes_restored": 0}
    if batch.status != "complete":
        raise PilotValidationError(
            f"schedule import {import_key!r} cannot roll back from {batch.status!r}"
        )
    before = await _stop_fingerprint(session)
    owned = (
        await session.scalars(
            select(TransitScheduleRoute).where(TransitScheduleRoute.schedule_import_id == batch.id)
        )
    ).all()
    backups = batch.report.get("route_backups", {})
    removed = 0
    restored = 0
    await session.execute(
        delete(TransitServiceProfile).where(TransitServiceProfile.schedule_import_id == batch.id)
    )
    await session.execute(delete(TransitTrip).where(TransitTrip.schedule_import_id == batch.id))
    for ownership in owned:
        if ownership.created_route:
            database_route = await session.get(TransitRoute, ownership.route_id)
            if database_route is not None:
                await session.execute(
                    delete(RouteStop).where(RouteStop.route_id == ownership.route_id)
                )
                await session.delete(database_route)
                removed += 1
            continue
        backup = backups.get(str(ownership.route_id))
        if backup is None:
            raise PilotValidationError(f"missing rollback data for route {ownership.route_id}")
        database_route = await session.get(TransitRoute, ownership.route_id)
        if database_route is None:
            raise PilotValidationError(f"route {ownership.route_id} disappeared before rollback")
        database_route.headway_min = backup["headway_min"]
        database_route.fare_idr = backup["fare_idr"]
        database_route.source = backup["source"]
        await session.execute(delete(RouteStop).where(RouteStop.route_id == ownership.route_id))
        old_rows = [
            {
                "route_id": ownership.route_id,
                "seq": row[0],
                "stop_id": row[1],
                "travel_time_from_prev_s": row[2],
            }
            for row in backup["route_stops"]
        ]
        if old_rows:
            await session.execute(pg_insert(RouteStop).values(old_rows))
        restored += 1
    await session.flush()
    if await _stop_fingerprint(session) != before:
        await session.rollback()
        raise RuntimeError("schedule rollback modified canonical transit_stops")
    batch.status = "rolled_back"
    await session.commit()
    return {
        "schedule_import_id": batch.id,
        "routes_removed": removed,
        "routes_restored": restored,
    }
