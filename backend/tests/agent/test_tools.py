from contextlib import asynccontextmanager

import pytest

from app.agent.tools import (
    ViewportTooLargeError,
    make_calculate_carbon_savings_tool,
    make_calculate_route_tool,
    make_get_data_in_viewport_tool,
    make_plan_multistop_tool,
    make_toggle_layer_tool,
)
from app.models.geo import BBox, Coord
from app.models.mapid import Feature
from app.models.routing import EmissionFactor
from app.routing.graph import GraphBuilder


async def test_toggle_layer_tool_returns_typed_result():
    t = make_toggle_layer_tool()
    result = await t.ainvoke({"layer_id": "transjogja", "on": True})
    assert result.layer_id == "transjogja"
    assert result.on is True


async def test_get_data_in_viewport_rejects_oversized_bbox_without_touching_db():
    def session_factory():
        raise AssertionError("DB should not be touched when the bbox is rejected")

    t = make_get_data_in_viewport_tool(session_factory, max_area_deg2=0.01)
    huge_bbox = BBox(min_lon=110.0, min_lat=-8.0, max_lon=111.0, max_lat=-7.0)
    with pytest.raises(ViewportTooLargeError):
        await t.ainvoke({"bbox": huge_bbox.model_dump(), "data_type": "poi", "limit": 10})


async def test_get_data_in_viewport_queries_db(db_session):
    from app.data.repository import upsert_poi

    feature = Feature(
        external_id="viewport1",
        properties={"nama_tempat": "Warung Test"},
        geometry={"type": "Point", "coordinates": [110.37, -7.80]},
    )
    await upsert_poi(db_session, [feature], "menugo")

    @asynccontextmanager
    async def session_factory():
        yield db_session

    t = make_get_data_in_viewport_tool(session_factory)
    small_bbox = BBox(min_lon=110.30, min_lat=-7.85, max_lon=110.45, max_lat=-7.75)
    results = await t.ainvoke({"bbox": small_bbox.model_dump(), "data_type": "poi", "limit": 10})
    assert any(f.external_id == "viewport1" for f in results)


def _line_graph():
    b = GraphBuilder()
    for u, v, length in [("A", "B", 1000), ("B", "C", 1000), ("A", "C", 5000)]:
        b.add_walk_edge(u, v, length)
        b.add_walk_edge(v, u, length)
    return b.build()


class _NullGeocodeResolver:
    async def forward(self, query: str):
        return None


async def test_calculate_route_tool_resolves_known_node_ids():
    graph = _line_graph()
    coords = {"A": (110.30, -7.80), "B": (110.31, -7.80), "C": (110.32, -7.80)}
    t = make_calculate_route_tool(lambda: graph, lambda: coords, _NullGeocodeResolver())

    route = await t.ainvoke({"start": "A", "end": "C", "modes": [], "optimize": "tercepat"})
    assert route.legs[0].from_node == "A"
    assert route.legs[-1].to_node == "C"


async def test_calculate_route_tool_snaps_a_coord_to_nearest_node():
    graph = _line_graph()
    coords = {"A": (110.30, -7.80), "B": (110.31, -7.80), "C": (110.32, -7.80)}
    t = make_calculate_route_tool(lambda: graph, lambda: coords, _NullGeocodeResolver())

    near_a = Coord(lat=-7.80, lon=110.300001)
    route = await t.ainvoke(
        {"start": near_a.model_dump(), "end": "C", "modes": [], "optimize": "tercepat"}
    )
    assert route.legs[0].from_node == "A"


async def test_plan_multistop_tool_orders_stops():
    graph = _line_graph()
    coords = {"A": (110.30, -7.80), "B": (110.31, -7.80), "C": (110.32, -7.80)}
    t = make_plan_multistop_tool(lambda: graph, lambda: coords, _NullGeocodeResolver())

    # Nearest-neighbour anchors on the first stop given ("C"); on this line topology
    # (A-B-C) the cost-optimal visiting order from C is C -> B -> A.
    itinerary = await t.ainvoke({"stops": ["C", "A", "B"], "optimize": "tercepat"})
    assert itinerary.stop_order == ["C", "B", "A"]


async def test_calculate_carbon_savings_tool_uses_primary_mode():
    graph = _line_graph()
    coords = {"A": (110.30, -7.80), "B": (110.31, -7.80), "C": (110.32, -7.80)}
    route_tool = make_calculate_route_tool(lambda: graph, lambda: coords, _NullGeocodeResolver())
    route = await route_tool.ainvoke(
        {"start": "A", "end": "C", "modes": [], "optimize": "tercepat"}
    )

    factors = {
        "walk": EmissionFactor(mode="walk", g_co2_per_km=0.0, source_citation="n/a"),
        "private_vehicle": EmissionFactor(
            mode="private_vehicle", g_co2_per_km=192.0, source_citation="KLHK 2023"
        ),
    }
    t = make_calculate_carbon_savings_tool(lambda: factors)
    result = await t.ainvoke({"route": route.model_dump()})
    assert result.mode == "walk"
    assert result.saved_g_co2 == pytest.approx(192.0 * (route.total_distance_m / 1000))
