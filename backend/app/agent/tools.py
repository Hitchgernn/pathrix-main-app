from collections.abc import Awaitable, Callable

import networkx as nx
from langchain_core.tools import BaseTool, tool

from app.data.geocode import GeocodeResolver
from app.data.repository import ViewportDataType, query_features_in_viewport
from app.models.agent import LayerResult
from app.models.geo import BBox, Coord
from app.models.mapid import Feature
from app.models.routing import CarbonResult, EmissionFactor, Itinerary, Optimize, Route
from app.routing.carbon import calculate_carbon_savings as routing_calculate_carbon_savings
from app.routing.constants import W_TRANSFER, W_WALK
from app.routing.graph import nearest_node
from app.routing.multistop import plan_multistop as routing_plan_multistop
from app.routing.shortest_path import calculate_route as routing_calculate_route

MAX_VIEWPORT_AREA_DEG2 = 0.25


class ViewportTooLargeError(Exception):
    pass


def _bbox_area(bbox: BBox) -> float:
    return abs(bbox.max_lon - bbox.min_lon) * abs(bbox.max_lat - bbox.min_lat)


def _objective_scalar(route: Route, optimize: Optimize) -> float:
    if optimize == "tercepat":
        return route.total_time_s
    if optimize == "termurah":
        return float(route.total_fare_idr)
    walk_m = sum(leg.distance_m for leg in route.legs if leg.mode == "walk")
    return route.transfers * W_TRANSFER + walk_m * W_WALK


def _primary_mode(route: Route) -> str:
    for leg in route.legs:
        if leg.mode in ("andong", "becak"):
            return leg.mode
    if any(leg.mode == "ride" for leg in route.legs):
        return (
            "bus"  # edge type has no operator identity yet; bus covers the common TransJogja case
        )
    return "walk"


def make_toggle_layer_tool() -> BaseTool:
    async def toggle_layer(layer_id: str, on: bool) -> LayerResult:
        """Turn a map layer on or off."""
        return LayerResult(layer_id=layer_id, on=on)

    return tool(toggle_layer)


def make_get_data_in_viewport_tool(
    session_factory: Callable[[], Awaitable],
    max_area_deg2: float = MAX_VIEWPORT_AREA_DEG2,
) -> BaseTool:
    async def get_data_in_viewport(
        bbox: BBox, data_type: ViewportDataType, limit: int = 50
    ) -> list[Feature]:
        """List features of a data type within the current map viewport."""
        if _bbox_area(bbox) > max_area_deg2:
            raise ViewportTooLargeError(
                f"viewport area {_bbox_area(bbox):.4f} deg^2 exceeds cap {max_area_deg2} deg^2"
            )
        async with session_factory() as session:
            return await query_features_in_viewport(session, data_type, bbox, limit)

    return tool(get_data_in_viewport)


async def _resolve_node(
    query: str | Coord, coords: dict[str, tuple[float, float]], geocode_resolver: GeocodeResolver
) -> str:
    if isinstance(query, Coord):
        return nearest_node(coords, (query.lon, query.lat))
    if query in coords:
        return query
    resolved = await geocode_resolver.forward(query)
    if resolved is None:
        raise ValueError(f"could not resolve location: {query!r}")
    return nearest_node(coords, (resolved.lon, resolved.lat))


def make_calculate_route_tool(
    graph_provider: Callable[[], nx.MultiDiGraph],
    coords_provider: Callable[[], dict[str, tuple[float, float]]],
    geocode_resolver: GeocodeResolver,
) -> BaseTool:
    async def calculate_route(
        start: str | Coord, end: str | Coord, modes: list[str], optimize: Optimize
    ) -> Route:
        """Compute a route between two places, optimizing for time, fare, or ease."""
        coords = coords_provider()
        start_node = await _resolve_node(start, coords, geocode_resolver)
        end_node = await _resolve_node(end, coords, geocode_resolver)
        allowed = set(modes) if modes else None
        return routing_calculate_route(
            graph_provider(), start_node, end_node, optimize, allowed_modes=allowed
        )

    return tool(calculate_route)


def make_plan_multistop_tool(
    graph_provider: Callable[[], nx.MultiDiGraph],
    coords_provider: Callable[[], dict[str, tuple[float, float]]],
    geocode_resolver: GeocodeResolver,
) -> BaseTool:
    async def plan_multistop(stops: list[str | Coord], optimize: Optimize) -> Itinerary:
        """Order a list of stops into an efficient multi-stop itinerary."""
        graph = graph_provider()
        coords = coords_provider()
        nodes = [await _resolve_node(stop, coords, geocode_resolver) for stop in stops]

        pair_routes: dict[tuple[int, int], Route] = {}
        n = len(nodes)
        cost_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                leg = routing_calculate_route(graph, nodes[i], nodes[j], optimize)
                pair_routes[(i, j)] = leg
                cost_matrix[i][j] = _objective_scalar(leg, optimize)

        index_by_node = {node: idx for idx, node in enumerate(nodes)}
        ordered_nodes, _ = routing_plan_multistop(nodes, cost_matrix)
        ordered_indices = [index_by_node[node] for node in ordered_nodes]

        legs = [
            pair_routes[(ordered_indices[i], ordered_indices[i + 1])]
            for i in range(len(ordered_indices) - 1)
        ]
        return Itinerary(
            stop_order=ordered_nodes,
            legs=legs,
            total_time_s=sum(leg.total_time_s for leg in legs),
            total_fare_idr=sum(leg.total_fare_idr for leg in legs),
        )

    return tool(plan_multistop)


def make_calculate_carbon_savings_tool(
    factors_provider: Callable[[], dict[str, EmissionFactor]],
) -> BaseTool:
    async def calculate_carbon_savings(route: Route) -> CarbonResult:
        """Compute grams of CO2 saved by a route versus a private vehicle."""
        mode = _primary_mode(route)
        return routing_calculate_carbon_savings(
            route.total_distance_m / 1000, mode, factors_provider()
        )

    return tool(calculate_carbon_savings)
