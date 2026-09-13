import pytest

from app.agent.demo_route import DEMO_ROUTE, make_demo_calculate_route_tool


def test_demo_route_legs_have_drawable_geometry_where_expected():
    walk, board, ride, alight, walk_to_andong, andong = DEMO_ROUTE.legs
    assert walk.mode == "walk"
    assert len(walk.coordinates) >= 2
    assert ride.mode == "ride"
    assert len(ride.coordinates) >= 2
    # board/alight are logical (waiting/stepping off), not a drawn segment.
    assert board.coordinates == []
    assert alight.coordinates == []
    assert walk_to_andong.mode == "walk"
    assert walk_to_andong.to_name == "Andong Malioboro"
    assert len(walk_to_andong.coordinates) >= 2
    assert andong.mode == "andong"
    assert andong.to_name == "Titik Nol Kilometer"
    assert andong.fare_idr > 0
    assert len(andong.coordinates) >= 2


def test_demo_route_totals_match_leg_sums():
    total_time = sum(leg.time_s for leg in DEMO_ROUTE.legs)
    total_fare = sum(leg.fare_idr for leg in DEMO_ROUTE.legs)
    total_distance = sum(leg.distance_m for leg in DEMO_ROUTE.legs)
    assert DEMO_ROUTE.total_time_s == pytest.approx(total_time)
    assert DEMO_ROUTE.total_fare_idr == total_fare
    assert DEMO_ROUTE.total_distance_m == pytest.approx(total_distance)


async def test_demo_tool_returns_fixture_regardless_of_input():
    route_tool = make_demo_calculate_route_tool()

    result = await route_tool.ainvoke(
        {"start": "anywhere", "end": "somewhere else", "modes": [], "optimize": "tercepat"}
    )

    assert result == DEMO_ROUTE
