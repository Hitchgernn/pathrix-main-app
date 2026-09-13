import networkx as nx

from app.models.routing import Optimize, Route, RouteLeg, RouteStopDetail, RouteStopSurvey
from app.routing.weights import BASE_WEIGHTS, multigraph_weight


class NoRouteFoundError(Exception):
    pass


def _coord(graph: nx.MultiDiGraph, node: str) -> list[float] | None:
    attrs = graph.nodes[node]
    lon, lat = attrs.get("lon"), attrs.get("lat")
    return None if lon is None or lat is None else [lon, lat]


def _name(graph: nx.MultiDiGraph, node: str) -> str | None:
    return graph.nodes[node].get("name")


def _leg_coordinates(graph: nx.MultiDiGraph, u: str, v: str) -> list[list[float]]:
    """A leg is drawable only if both ends are pinned. Half a line is worse than
    none, so an unpinned endpoint yields no geometry at all."""
    start, end = _coord(graph, u), _coord(graph, v)
    return [] if start is None or end is None else [start, end]


def _restrict_modes(graph: nx.MultiDiGraph, allowed_modes: set[str]) -> nx.MultiDiGraph:
    kept_edges = [
        (u, v, k)
        for u, v, k, d in graph.edges(keys=True, data=True)
        if d["type"] in allowed_modes or d.get("transit_mode") in allowed_modes
    ]
    return graph.edge_subgraph(kept_edges)


def _route_stops(graph: nx.MultiDiGraph, path: list[str]) -> list[RouteStopDetail]:
    stops: list[RouteStopDetail] = []
    seen: set[int] = set()
    for node in path:
        detail = graph.nodes[node].get("stop_detail")
        if not detail or detail["id"] in seen:
            continue
        seen.add(detail["id"])
        survey = None
        if detail.get("surveyor") or detail.get("community") or detail.get("surveyed_at"):
            survey = RouteStopSurvey(
                by=detail.get("surveyor"),
                community=detail.get("community"),
                at=detail.get("surveyed_at"),
            )
        services = detail.get("routes", [])
        schedule_meta = next(
            (service for service in services if service.get("freshness_status")), None
        )
        external_id = detail.get("external_id")
        stops.append(
            RouteStopDetail(
                id=external_id or f"transit:{detail['id']}",
                database_id=detail["id"],
                external_id=external_id,
                name=detail.get("name"),
                coord=[detail["lon"], detail["lat"]],
                photo_url=detail.get("photo_url"),
                photos=detail.get("photos", []),
                description=detail.get("description"),
                survey=survey,
                routes=services,
                source=detail.get("source"),
                effective_from=(schedule_meta or {}).get("effective_from"),
                freshness_status=(schedule_meta or {}).get("freshness_status"),
            )
        )
    return stops


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
                from_name=_name(graph, u),
                to_name=_name(graph, v),
                transit_mode=attrs.get("transit_mode"),
                service_name=attrs.get("service_name"),
                operator=attrs.get("operator"),
                source=attrs.get("source"),
                coordinates=attrs.get("coordinates") or _leg_coordinates(graph, u, v),
            )
        )

    return Route(
        legs=legs,
        stops=_route_stops(graph, path),
        total_time_s=sum(leg.time_s for leg in legs),
        total_fare_idr=sum(leg.fare_idr for leg in legs),
        total_distance_m=sum(leg.distance_m for leg in legs),
        transfers=max(
            max(0, sum(1 for leg in legs if leg.mode == "board") - 1),
            sum(1 for leg in legs if leg.mode == "transfer"),
        ),
    )
