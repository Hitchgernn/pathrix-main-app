import networkx as nx
from shapely import MultiPoint, Polygon, concave_hull

from app.routing.weights import multigraph_weight


def compute_isochrone(
    graph: nx.MultiDiGraph,
    source: str,
    cutoff_s: float,
    coords: dict[str, tuple[float, float]],
    ratio: float = 0.3,
) -> Polygon:
    reachable = nx.single_source_dijkstra_path_length(
        graph, source, cutoff=cutoff_s, weight=multigraph_weight("tercepat")
    )
    points = [coords[node] for node in reachable if node in coords]
    if len(points) < 3:
        raise ValueError("fewer than 3 reachable nodes have coordinates; cannot build a hull")

    return concave_hull(MultiPoint(points), ratio=ratio)
