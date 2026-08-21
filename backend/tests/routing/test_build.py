from app.models.network import (
    NetworkData,
    PangkalanRow,
    RouteRow,
    RouteStopRow,
    StopRow,
    WalkEdgeRow,
    WalkNodeRow,
)
from app.routing.build import (
    PANGKALAN_CONNECT_RADIUS_M,
    build_graph_from_network,
    pangkalan_node,
    stop_node,
    walk_node,
)
from app.routing.graph import GraphBuilder
from app.routing.shortest_path import NoRouteFoundError, calculate_route


def test_empty_network_produces_an_empty_graph():
    graph, coords = build_graph_from_network(
        NetworkData(stops=[], routes=[], route_stops=[], pangkalan=[])
    )
    assert graph.number_of_nodes() == 0
    assert coords == {}


def test_a_route_connects_its_stops_via_board_ride_alight():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.30, lat=-7.80), StopRow(id=2, lon=110.35, lat=-7.82)],
        routes=[RouteRow(id=10, headway_min=10, fare_idr=3500)],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=600),
        ],
        pangkalan=[],
    )
    graph, coords = build_graph_from_network(network)

    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat")
    assert [leg.mode for leg in route.legs] == ["board", "ride", "alight"]
    assert route.total_fare_idr == 3500
    assert coords[stop_node(1)] == (110.30, -7.80)


def test_missing_travel_time_skips_that_ride_edge():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.30, lat=-7.80), StopRow(id=2, lon=110.35, lat=-7.82)],
        routes=[RouteRow(id=10, headway_min=10, fare_idr=3500)],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=None),
        ],
        pangkalan=[],
    )
    graph, _ = build_graph_from_network(network)
    try:
        calculate_route(graph, stop_node(1), stop_node(2), "tercepat")
        raised = False
    except NoRouteFoundError:
        raised = True
    assert raised


def test_pangkalan_connects_only_within_radius():
    near_stop = StopRow(id=1, lon=110.30, lat=-7.80)
    far_stop = StopRow(id=2, lon=110.50, lat=-7.95)  # far outside PANGKALAN_CONNECT_RADIUS_M
    pangkalan = PangkalanRow(
        id=5, type="andong", lon=110.3002, lat=-7.8002, fare_base=5000, fare_per_km=2000
    )
    network = NetworkData(
        stops=[near_stop, far_stop], routes=[], route_stops=[], pangkalan=[pangkalan]
    )

    graph, coords = build_graph_from_network(network)

    assert graph.has_edge(pangkalan_node(5), stop_node(1))
    assert not graph.has_edge(pangkalan_node(5), stop_node(2))
    assert coords[pangkalan_node(5)] == (110.3002, -7.8002)
    assert PANGKALAN_CONNECT_RADIUS_M == 500.0


def test_walk_network_connects_two_stops_with_no_route_between_them():
    # Two isolated stops, no shared route, no pangkalan — only reachable
    # through the walk network snapping each stop to its nearest walk node.
    stop_a = StopRow(id=1, lon=110.300, lat=-7.800)
    stop_b = StopRow(id=2, lon=110.302, lat=-7.800)
    network = NetworkData(
        stops=[stop_a, stop_b],
        routes=[],
        route_stops=[],
        pangkalan=[],
        walk_nodes=[
            WalkNodeRow(id=1, lon=110.3005, lat=-7.800),
            WalkNodeRow(id=2, lon=110.3015, lat=-7.800),
        ],
        walk_edges=[WalkEdgeRow(u=1, v=2, length_m=100.0), WalkEdgeRow(u=2, v=1, length_m=100.0)],
    )

    graph, coords = build_graph_from_network(network)

    assert graph.has_edge(walk_node(1), walk_node(2))
    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat")
    assert all(leg.mode == "walk" for leg in route.legs)
    assert route.total_fare_idr == 0
    assert coords[walk_node(1)] == (110.3005, -7.800)


def test_route_legs_carry_drawable_coordinates():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.30, lat=-7.80), StopRow(id=2, lon=110.35, lat=-7.82)],
        routes=[RouteRow(id=10, headway_min=10, fare_idr=3500)],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=600),
        ],
        pangkalan=[],
    )
    graph, _ = build_graph_from_network(network)

    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat")

    # Every leg is drawable — the ride leg included, since a route node sits at
    # its stop rather than floating unpinned.
    assert all(len(leg.coordinates) == 2 for leg in route.legs)
    ride = next(leg for leg in route.legs if leg.mode == "ride")
    assert ride.coordinates == [[110.30, -7.80], [110.35, -7.82]]


def test_unpinned_nodes_yield_no_leg_geometry():
    # A graph built by hand, with no coordinates set: costs still compute, but
    # nothing is drawable, and the contract says so with an empty list.
    builder = GraphBuilder()
    builder.add_walk_edge("A", "B", 100.0)
    route = calculate_route(builder.build(), "A", "B", "tercepat")

    assert [leg.coordinates for leg in route.legs] == [[]]
