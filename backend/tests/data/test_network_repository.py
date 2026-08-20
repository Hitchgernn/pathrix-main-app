from sqlalchemy import func, insert

from app.data.repository import fetch_emission_factors, fetch_network_data, upsert_walk_network
from app.data.schema import EmissionFactor, Pangkalan, RouteStop, TransitRoute, TransitStop
from app.models.network import WalkEdgeRow, WalkNodeRow


async def test_fetch_network_data_returns_seeded_rows(db_session):
    stop_result = await db_session.execute(
        insert(TransitStop)
        .values(
            name="Halte A",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.30, -7.80), 4326),
            source="test",
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
            source="test",
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
