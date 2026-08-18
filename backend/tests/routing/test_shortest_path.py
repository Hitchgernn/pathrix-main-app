import pytest

from app.routing.graph import GraphBuilder
from app.routing.shortest_path import NoRouteFoundError, calculate_route


def _diamond_graph():
    """A -> B -> D is short/expensive; A -> C -> D is long/cheap.

    A --walk 1000m-- B --walk 1000m-- D   (fast, no fare)
    A --andong 500m-- C --andong 500m-- D  (fare charged, but slower start cost)
    """
    b = GraphBuilder()
    b.add_walk_edge("A", "B", 1000)
    b.add_walk_edge("B", "D", 1000)
    b.add_andong_edge("A", "C", 5000, speed_mps=2.0, fare_base=5000, fare_per_km=2000)
    b.add_andong_edge("C", "D", 5000, speed_mps=2.0, fare_base=5000, fare_per_km=2000)
    return b.build()


def test_tercepat_prefers_the_faster_walk_path():
    graph = _diamond_graph()
    route = calculate_route(graph, "A", "D", "tercepat")
    assert [leg.mode for leg in route.legs] == ["walk", "walk"]
    assert route.total_fare_idr == 0


def _fare_vs_free_graph():
    """A->B direct board is fast but priced; A->C->B walk-only is slow but free."""
    b = GraphBuilder()
    b.add_board_edge("A", "B", headway_min=5, fare_idr=3500)
    b.add_walk_edge("A", "C", 3000)
    b.add_walk_edge("C", "B", 3000)
    return b.build()


def test_tercepat_picks_the_priced_fast_path():
    graph = _fare_vs_free_graph()
    route = calculate_route(graph, "A", "B", "tercepat")
    assert [leg.mode for leg in route.legs] == ["board"]
    assert route.total_fare_idr == 3500


def test_termurah_picks_the_free_slow_path():
    graph = _fare_vs_free_graph()
    route = calculate_route(graph, "A", "B", "termurah")
    assert route.total_fare_idr == 0
    assert [leg.mode for leg in route.legs] == ["walk", "walk"]


def test_no_route_raises():
    graph = GraphBuilder().build()
    graph.add_node("A")
    graph.add_node("Z")
    with pytest.raises(NoRouteFoundError):
        calculate_route(graph, "A", "Z", "tercepat")


def test_termudah_avoids_transfer_when_a_no_transfer_option_exists():
    b = GraphBuilder()
    # Direct ride, no transfer.
    b.add_walk_edge("A", "B", 100)
    # Alternative path forces a transfer edge, cheaper in time but termudah penalizes transfers.
    b.add_transfer_edge("A", "T", walk_time_s=1, walk_m=1, headway_min=1, fare_idr=3500)
    b.add_walk_edge("T", "B", 1)
    graph = b.build()

    route = calculate_route(graph, "A", "B", "termudah")
    assert route.transfers == 0
    assert [leg.mode for leg in route.legs] == ["walk"]
