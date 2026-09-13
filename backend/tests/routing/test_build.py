from app.models.network import (
    NetworkData,
    PangkalanRow,
    RouteRow,
    RouteSegmentGeometryRow,
    RouteStopRow,
    StopRow,
    WalkEdgeRow,
    WalkNodeRow,
)
from app.routing.build import (
    PANGKALAN_CONNECT_RADIUS_M,
    WALK_NETWORK_SNAP_RADIUS_M,
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


def test_pangkalan_also_gets_a_walk_edge_for_last_mile():
    near_stop = StopRow(id=1, lon=110.30, lat=-7.80)
    pangkalan = PangkalanRow(
        id=5, type="becak", lon=110.3002, lat=-7.8002, fare_base=5000, fare_per_km=2000
    )
    network = NetworkData(stops=[near_stop], routes=[], route_stops=[], pangkalan=[pangkalan])

    graph, _ = build_graph_from_network(network)

    to_stop_types = {data["type"] for data in graph[pangkalan_node(5)][stop_node(1)].values()}
    to_pangkalan_types = {data["type"] for data in graph[stop_node(1)][pangkalan_node(5)].values()}
    assert to_stop_types == {"becak", "walk"}
    assert to_pangkalan_types == {"becak", "walk"}


def test_short_pangkalan_leg_prefers_walking_over_a_ride():
    near_stop = StopRow(id=1, lon=110.30, lat=-7.80)
    pangkalan = PangkalanRow(
        id=5, type="becak", lon=110.3002, lat=-7.8002, fare_base=5000, fare_per_km=2000
    )
    network = NetworkData(stops=[near_stop], routes=[], route_stops=[], pangkalan=[pangkalan])

    graph, _ = build_graph_from_network(network)

    route = calculate_route(graph, stop_node(1), pangkalan_node(5), "tercepat")
    assert [leg.mode for leg in route.legs] == ["walk"]
    assert route.total_fare_idr == 0


def test_walk_network_does_not_snap_a_stop_outside_its_local_area():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.300, lat=-7.800), StopRow(id=2, lon=110.500, lat=-7.950)],
        routes=[],
        route_stops=[],
        pangkalan=[],
        walk_nodes=[WalkNodeRow(id=1, lon=110.3005, lat=-7.800)],
    )

    graph, _ = build_graph_from_network(network)

    assert graph.has_edge(stop_node(1), walk_node(1))
    assert not graph.has_edge(stop_node(2), walk_node(1))
    assert WALK_NETWORK_SNAP_RADIUS_M == 500.0


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
        stops=[
            StopRow(id=1, lon=110.30, lat=-7.80, name="Halte A"),
            StopRow(id=2, lon=110.35, lat=-7.82, name="Halte B"),
        ],
        routes=[
            RouteRow(
                id=10,
                headway_min=10,
                fare_idr=3500,
                name="EV3",
                operator="TransJogja",
                mode="bus",
                source="transport-pdf:EV3;effective_from=2025-01-01;freshness_status=unverified",
            )
        ],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=600),
        ],
        pangkalan=[],
    )
    graph, _ = build_graph_from_network(network)

    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat", allowed_modes={"bus"})

    # Every leg is drawable — the ride leg included, since a route node sits at
    # its stop rather than floating unpinned.
    assert all(len(leg.coordinates) == 2 for leg in route.legs)
    ride = next(leg for leg in route.legs if leg.mode == "ride")
    assert ride.coordinates == [[110.30, -7.80], [110.35, -7.82]]
    assert ride.distance_m > 0
    assert ride.from_name == "Halte A"
    assert ride.to_name == "Halte B"
    assert ride.transit_mode == "bus"
    assert ride.service_name == "EV3"
    assert ride.operator == "TransJogja"
    assert ride.source and "freshness_status=unverified" in ride.source


def test_ride_leg_uses_stored_osm_segment_geometry_when_available():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.30, lat=-7.80), StopRow(id=2, lon=110.35, lat=-7.82)],
        routes=[
            RouteRow(
                id=10,
                headway_min=10,
                fare_idr=3500,
                name="EV3",
                operator="TransJogja",
                mode="bus",
                source="normalized-transport:EV3;routable=true",
                source_route_id="EV3",
            )
        ],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=1, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=2, travel_time_from_prev_s=600),
        ],
        route_segment_geometries=[
            RouteSegmentGeometryRow(
                route_id="EV3",
                from_stop_sequence=1,
                to_stop_sequence=2,
                coordinates=[[110.30, -7.80], [110.32, -7.81], [110.35, -7.82]],
                distance_m=6500,
            )
        ],
        pangkalan=[],
    )

    graph, _ = build_graph_from_network(network)
    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat", allowed_modes={"bus"})
    ride = next(leg for leg in route.legs if leg.mode == "ride")

    assert ride.coordinates == [[110.30, -7.80], [110.32, -7.81], [110.35, -7.82]]
    assert ride.distance_m == 6500


def test_unpinned_nodes_yield_no_leg_geometry():
    # A graph built by hand, with no coordinates set: costs still compute, but
    # nothing is drawable, and the contract says so with an empty list.
    builder = GraphBuilder()
    builder.add_walk_edge("A", "B", 100.0)
    route = calculate_route(builder.build(), "A", "B", "tercepat")

    assert [leg.coordinates for leg in route.legs] == [[]]


def test_route_deduplicates_rich_activity_stops():
    network = NetworkData(
        stops=[
            StopRow(
                id=1,
                external_id="activity-a",
                lon=110.30,
                lat=-7.80,
                name="Halte A",
                photo_url="https://img.example/a.jpg",
                photos=["https://img.example/a.jpg", "https://img.example/a-2.jpg"],
                description="Shelter beside the market",
                surveyor="Surveyor A",
                community="Community A",
                surveyed_at="2026-08-17T10:00:00Z",
                source="mapid_activities",
            ),
            StopRow(
                id=2,
                external_id="activity-b",
                lon=110.31,
                lat=-7.81,
                name="Halte B",
                source="mapid_activities",
            ),
        ],
        routes=[RouteRow(id=10, headway_min=10, fare_idr=3500, name="EV3")],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=300),
        ],
        pangkalan=[],
    )
    graph, _ = build_graph_from_network(network)

    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat")

    assert [stop.id for stop in route.stops] == ["activity-a", "activity-b"]
    assert route.stops[0].database_id == 1
    assert route.stops[0].coord == [110.30, -7.80]
    assert route.stops[0].photo_url == "https://img.example/a.jpg"
    assert route.stops[0].description == "Shelter beside the market"
    assert route.stops[0].survey and route.stops[0].survey.by == "Surveyor A"
    assert route.stops[0].source == "mapid_activities"
