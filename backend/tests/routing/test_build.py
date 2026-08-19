from app.models.network import NetworkData, PangkalanRow, RouteRow, RouteStopRow, StopRow
from app.routing.build import (
    PANGKALAN_CONNECT_RADIUS_M,
    build_graph_from_network,
    pangkalan_node,
    stop_node,
)
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
