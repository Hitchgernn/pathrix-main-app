import networkx as nx

from app.routing import edges


class GraphBuilder:
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def set_coord(self, node: str, lon: float, lat: float) -> None:
        """Pins a node to a position. Carried on the node rather than in a side
        dict so shortest_path can build drawable legs from the graph alone."""
        self.graph.add_node(node, lon=lon, lat=lat)

    def add_walk_edge(self, u: str, v: str, length_m: float) -> None:
        self.graph.add_edge(u, v, **edges.walk_edge_attrs(length_m))

    def add_board_edge(self, stop: str, route_node: str, headway_min: float, fare_idr: int) -> None:
        self.graph.add_edge(stop, route_node, **edges.board_edge_attrs(headway_min, fare_idr))

    def add_ride_edge(self, u: str, v: str, travel_time_s: float, distance_m: float = 0.0) -> None:
        self.graph.add_edge(u, v, **edges.ride_edge_attrs(travel_time_s, distance_m))

    def add_alight_edge(self, route_node: str, stop: str) -> None:
        self.graph.add_edge(route_node, stop, **edges.alight_edge_attrs())

    def add_transfer_edge(
        self,
        u: str,
        v: str,
        walk_time_s: float,
        walk_m: float,
        headway_min: float,
        fare_idr: int,
        free_transfer: bool = False,
    ) -> None:
        self.graph.add_edge(
            u,
            v,
            **edges.transfer_edge_attrs(walk_time_s, walk_m, headway_min, fare_idr, free_transfer),
        )

    def add_andong_edge(
        self,
        u: str,
        v: str,
        distance_m: float,
        speed_mps: float,
        fare_base: int,
        fare_per_km: float,
    ) -> None:
        self.graph.add_edge(
            u, v, **edges.andong_edge_attrs(distance_m, speed_mps, fare_base, fare_per_km)
        )

    def add_becak_edge(
        self,
        u: str,
        v: str,
        distance_m: float,
        speed_mps: float,
        fare_base: int,
        fare_per_km: float,
    ) -> None:
        self.graph.add_edge(
            u, v, **edges.becak_edge_attrs(distance_m, speed_mps, fare_base, fare_per_km)
        )

    def build(self) -> nx.MultiDiGraph:
        return self.graph


def nearest_node(coords: dict[str, tuple[float, float]], target: tuple[float, float]) -> str:
    if not coords:
        raise ValueError("coords is empty; cannot find a nearest node")

    def sq_dist(point: tuple[float, float]) -> float:
        return (point[0] - target[0]) ** 2 + (point[1] - target[1]) ** 2

    return min(coords, key=lambda node_id: sq_dist(coords[node_id]))
