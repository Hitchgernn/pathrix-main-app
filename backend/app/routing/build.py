import math

import networkx as nx

from app.models.network import NetworkData
from app.routing.graph import GraphBuilder, nearest_node

PANGKALAN_CONNECT_RADIUS_M = 500.0  # first/last-mile walk range — placeholder, untuned
ANDONG_SPEED_MPS = 2.2  # ~8 km/h
BECAK_SPEED_MPS = 3.3  # ~12 km/h

_EARTH_RADIUS_M = 6_371_000.0


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def stop_node(stop_id: int) -> str:
    return f"stop:{stop_id}"


def pangkalan_node(pangkalan_id: int) -> str:
    return f"pangkalan:{pangkalan_id}"


def _route_node(route_id: int, stop_id: int) -> str:
    return f"route:{route_id}:stop:{stop_id}"


def walk_node(osm_id: int) -> str:
    return f"walk:{osm_id}"


def build_graph_from_network(
    network: NetworkData,
) -> tuple[nx.MultiDiGraph, dict[str, tuple[float, float]]]:
    """Assembles the routing graph from already-fetched network rows.

    Stops connect to each other through route board/ride/alight edges, and to
    the pedestrian network (network.walk_nodes/walk_edges, from OSMnx via
    data/osm.py) by snapping each stop to its nearest walk node. When no walk
    network is present — the common case until an ETL run populates it —
    pangkalan still fall back to connecting directly to any stop within
    PANGKALAN_CONNECT_RADIUS_M, a stand-in for real walk distance.
    """
    builder = GraphBuilder()
    coords: dict[str, tuple[float, float]] = {}

    routes_by_id = {r.id: r for r in network.routes}
    stops_by_id = {s.id: s for s in network.stops}

    for stop in network.stops:
        coords[stop_node(stop.id)] = (stop.lon, stop.lat)
        builder.set_coord(stop_node(stop.id), stop.lon, stop.lat)

    stops_by_route: dict[int, list] = {}
    for rs in sorted(network.route_stops, key=lambda rs: (rs.route_id, rs.seq)):
        stops_by_route.setdefault(rs.route_id, []).append(rs)

    for route_id, ordered_stops in stops_by_route.items():
        route = routes_by_id.get(route_id)
        if route is None:
            continue
        for rs in ordered_stops:
            if rs.stop_id not in stops_by_id:
                continue
            # A route node sits at its stop: a ride leg between two route nodes
            # is drawn stop to stop, which is what the map needs.
            stop = stops_by_id[rs.stop_id]
            builder.set_coord(_route_node(route_id, rs.stop_id), stop.lon, stop.lat)
            builder.add_board_edge(
                stop_node(rs.stop_id),
                _route_node(route_id, rs.stop_id),
                route.headway_min,
                route.fare_idr,
            )
            builder.add_alight_edge(_route_node(route_id, rs.stop_id), stop_node(rs.stop_id))

        for prev_rs, rs in zip(ordered_stops, ordered_stops[1:], strict=False):
            if rs.travel_time_from_prev_s is None:
                continue
            if prev_rs.stop_id not in stops_by_id or rs.stop_id not in stops_by_id:
                continue
            builder.add_ride_edge(
                _route_node(route_id, prev_rs.stop_id),
                _route_node(route_id, rs.stop_id),
                rs.travel_time_from_prev_s,
            )

    for p in network.pangkalan:
        node = pangkalan_node(p.id)
        coords[node] = (p.lon, p.lat)
        builder.set_coord(node, p.lon, p.lat)
        speed = ANDONG_SPEED_MPS if p.type == "andong" else BECAK_SPEED_MPS
        add_edge = builder.add_andong_edge if p.type == "andong" else builder.add_becak_edge
        for stop in network.stops:
            distance_m = _haversine_m((p.lon, p.lat), (stop.lon, stop.lat))
            if distance_m > PANGKALAN_CONNECT_RADIUS_M:
                continue
            add_edge(node, stop_node(stop.id), distance_m, speed, p.fare_base, p.fare_per_km)
            add_edge(stop_node(stop.id), node, distance_m, speed, p.fare_base, p.fare_per_km)

    walk_coords: dict[str, tuple[float, float]] = {}
    for wn in network.walk_nodes:
        node = walk_node(wn.id)
        walk_coords[node] = (wn.lon, wn.lat)
        coords[node] = (wn.lon, wn.lat)
        builder.set_coord(node, wn.lon, wn.lat)

    for we in network.walk_edges:
        builder.add_walk_edge(walk_node(we.u), walk_node(we.v), we.length_m)

    if walk_coords:
        for stop in network.stops:
            nearest = nearest_node(walk_coords, (stop.lon, stop.lat))
            distance_m = _haversine_m((stop.lon, stop.lat), walk_coords[nearest])
            builder.add_walk_edge(stop_node(stop.id), nearest, distance_m)
            builder.add_walk_edge(nearest, stop_node(stop.id), distance_m)

        for p in network.pangkalan:
            node = pangkalan_node(p.id)
            nearest = nearest_node(walk_coords, (p.lon, p.lat))
            distance_m = _haversine_m((p.lon, p.lat), walk_coords[nearest])
            builder.add_walk_edge(node, nearest, distance_m)
            builder.add_walk_edge(nearest, node, distance_m)

    return builder.build(), coords
