import pytest
from shapely import Point

from app.routing.graph import GraphBuilder
from app.routing.isochrone import compute_isochrone


def _star_graph():
    b = GraphBuilder()
    b.add_walk_edge("center", "near", 100)  # ~75s
    b.add_walk_edge("center", "mid", 500)  # ~376s
    b.add_walk_edge("center", "far", 5000)  # ~3759s, should be excluded by a tight cutoff
    return b.build()


def test_isochrone_only_includes_nodes_within_cutoff():
    graph = _star_graph()
    coords = {
        "center": (110.30, -7.80),
        "near": (110.31, -7.80),
        "mid": (110.32, -7.81),
        "far": (110.50, -7.90),
    }
    polygon = compute_isochrone(graph, "center", cutoff_s=500, coords=coords)

    assert polygon.contains(Point(coords["near"])) or polygon.touches(Point(coords["near"]))
    assert not polygon.contains(Point(coords["far"]))


def test_isochrone_raises_with_too_few_reachable_points():
    graph = _star_graph()
    coords = {"center": (110.30, -7.80), "near": (110.31, -7.80)}
    with pytest.raises(ValueError):
        compute_isochrone(graph, "center", cutoff_s=10, coords=coords)
