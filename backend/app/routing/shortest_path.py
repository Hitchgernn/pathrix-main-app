import networkx as nx

from app.models.routing import Optimize, Route, RouteLeg
from app.routing.weights import BASE_WEIGHTS, multigraph_weight


class NoRouteFoundError(Exception):
    pass


def _restrict_modes(graph: nx.MultiDiGraph, allowed_modes: set[str]) -> nx.MultiDiGraph:
    kept_edges = [
        (u, v, k) for u, v, k, d in graph.edges(keys=True, data=True) if d["type"] in allowed_modes
    ]
    return graph.edge_subgraph(kept_edges)


def calculate_route(
    graph: nx.MultiDiGraph,
    start: str,
    end: str,
    optimize: Optimize,
    allowed_modes: set[str] | None = None,
) -> Route:
    if allowed_modes is not None:
        graph = _restrict_modes(graph, allowed_modes | {"walk"})

    try:
        path = nx.shortest_path(graph, start, end, weight=multigraph_weight(optimize))
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        raise NoRouteFoundError(f"no route from {start} to {end}") from exc

    base_weight = BASE_WEIGHTS[optimize]
    legs = []
    for u, v in zip(path, path[1:], strict=False):
        parallel_edges = graph[u][v]
        _, attrs = min(parallel_edges.items(), key=lambda kv: base_weight(kv[1]))
        legs.append(
            RouteLeg(
                mode=attrs["type"],
                from_node=str(u),
                to_node=str(v),
                time_s=attrs["time_s"],
                fare_idr=attrs["fare_idr"],
                distance_m=attrs["distance_m"],
            )
        )

    return Route(
        legs=legs,
        total_time_s=sum(leg.time_s for leg in legs),
        total_fare_idr=sum(leg.fare_idr for leg in legs),
        total_distance_m=sum(leg.distance_m for leg in legs),
        transfers=sum(1 for leg in legs if leg.mode == "transfer"),
    )
