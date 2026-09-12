from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, insert

from app.data.repository import (
    fetch_emission_factors,
    fetch_network_data,
    fetch_stop_departures,
    upsert_walk_network,
)
from app.data.schema import (
    EmissionFactor,
    Pangkalan,
    RouteStop,
    TransitRoute,
    TransitScheduleImport,
    TransitStop,
    TransitStopTime,
    TransitTrip,
)
from app.models.network import WalkEdgeRow, WalkNodeRow


async def test_fetch_network_data_returns_seeded_rows(db_session):
    stop_result = await db_session.execute(
        insert(TransitStop)
        .values(
            external_id="activity-halte-a",
            name="Halte A",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.30, -7.80), 4326),
            raw={
                "description": "Shelter dekat pasar",
                "medias": ["https://img.example/halte-a.jpg"],
                "user_full_name": "Surveyor A",
                "community_name": "Komunitas A",
                "created_at": "2026-08-17T10:00:00Z",
            },
            source="mapid_activities",
        )
        .returning(TransitStop.id)
    )
    stop_id = stop_result.scalar_one()

    route_result = await db_session.execute(
        insert(TransitRoute)
        .values(
            name="1A",
            operator="TransJogja",
            mode="bus",
            headway_min=10,
            fare_idr=3500,
            source="transport-pdf:1A;effective_from=2025-01-01;freshness_status=unverified",
        )
        .returning(TransitRoute.id)
    )
    route_id = route_result.scalar_one()

    await db_session.execute(
        insert(RouteStop).values(
            route_id=route_id, stop_id=stop_id, seq=0, travel_time_from_prev_s=None
        )
    )
    await db_session.execute(
        insert(Pangkalan).values(
            type="andong",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.301, -7.801), 4326),
            fare_base=5000,
            fare_per_km=2000,
        )
    )
    await db_session.commit()

    network = await fetch_network_data(db_session)

    assert len(network.stops) == 1
    assert network.stops[0].id == stop_id
    assert network.stops[0].lon == 110.30
    assert network.stops[0].external_id == "activity-halte-a"
    assert network.stops[0].photo_url == "https://img.example/halte-a.jpg"
    assert network.stops[0].description == "Shelter dekat pasar"
    assert network.stops[0].surveyor == "Surveyor A"
    assert network.stops[0].routes[0].name == "1A"
    assert network.stops[0].routes[0].freshness_status == "unverified"
    assert len(network.routes) == 1
    assert network.routes[0].fare_idr == 3500
    assert len(network.route_stops) == 1
    assert len(network.pangkalan) == 1
    assert network.pangkalan[0].fare_base == 5000


async def test_fetch_network_data_skips_pangkalan_missing_fares(db_session):
    await db_session.execute(
        insert(Pangkalan).values(
            type="becak", geom=func.ST_SetSRID(func.ST_MakePoint(110.30, -7.80), 4326)
        )
    )
    await db_session.commit()

    network = await fetch_network_data(db_session)
    assert network.pangkalan == []


async def test_fetch_stop_departures_rejects_invalid_local_time(db_session):
    with pytest.raises(ValueError, match="valid HH:MM"):
        await fetch_stop_departures(db_session, "activity-halte-a", after_local="29:99")


async def test_fetch_stop_departures_joins_only_canonical_activity_stop(db_session):
    stop_id = await db_session.scalar(
        insert(TransitStop)
        .values(
            external_id="activity-departure-stop",
            name="Halte Jadwal",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.30, -7.80), 4326),
            raw={"medias": ["https://img.example/stop.jpg"]},
            source="mapid_activities",
        )
        .returning(TransitStop.id)
    )
    route_id = await db_session.scalar(
        insert(TransitRoute)
        .values(
            name="EV3",
            operator="TransJogja",
            mode="bus",
            headway_min=10,
            fare_idr=3500,
            source="transportation-data/trans-jogja.csv",
        )
        .returning(TransitRoute.id)
    )
    schedule_import_id = await db_session.scalar(
        insert(TransitScheduleImport)
        .values(
            import_key=f"test-{uuid4()}",
            source_digest="abc123",
            source_path="transportation-data/trans-jogja.csv",
            status="complete",
            effective_from=date(2025, 1, 1),
            freshness_as_of=date(2026, 9, 12),
            freshness_status="unverified",
            report={},
        )
        .returning(TransitScheduleImport.id)
    )
    trip_id = await db_session.scalar(
        insert(TransitTrip)
        .values(
            schedule_import_id=schedule_import_id,
            route_id=route_id,
            external_id="EV3-0800",
            is_estimated=False,
            provenance={},
        )
        .returning(TransitTrip.id)
    )
    await db_session.execute(
        insert(TransitStopTime).values(
            trip_id=trip_id,
            stop_id=stop_id,
            seq=1,
            scheduled_time_local="08:10",
            day_offset=0,
            is_estimated=False,
        )
    )
    await db_session.commit()

    departures = await fetch_stop_departures(
        db_session,
        "activity-departure-stop",
        after_local="08:00",
    )

    assert len(departures) == 1
    assert departures[0].service_name == "EV3"
    assert departures[0].scheduled_time_local == "08:10"
    assert departures[0].freshness_status == "unverified"
    assert departures[0].source == "transportation-data/trans-jogja.csv"


async def test_upsert_walk_network_is_idempotent_and_fetch_returns_it(db_session):
    nodes = [
        WalkNodeRow(id=101, lon=110.30, lat=-7.80),
        WalkNodeRow(id=102, lon=110.301, lat=-7.801),
    ]
    edges = [WalkEdgeRow(u=101, v=102, length_m=50.0)]

    count1 = await upsert_walk_network(db_session, nodes, edges)
    assert count1 == (2, 1)

    updated_edges = [WalkEdgeRow(u=101, v=102, length_m=60.0)]
    count2 = await upsert_walk_network(db_session, nodes, updated_edges)
    assert count2 == (2, 1)

    network = await fetch_network_data(db_session)
    assert {n.id for n in network.walk_nodes} == {101, 102}
    assert len(network.walk_edges) == 1
    assert network.walk_edges[0].length_m == 60.0


async def test_fetch_emission_factors_returns_a_mode_keyed_dict(db_session):
    await db_session.execute(
        insert(EmissionFactor).values(mode="bus", g_co2_per_km=68.0, source_citation="IPCC 2021")
    )
    await db_session.commit()

    factors = await fetch_emission_factors(db_session)
    assert factors["bus"].g_co2_per_km == 68.0
    assert factors["bus"].source_citation == "IPCC 2021"
