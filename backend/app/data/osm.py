import asyncio
from typing import Protocol

from shapely import Polygon

from app.models.network import WalkEdgeRow, WalkNodeRow


class WalkNetworkFetcher(Protocol):
    async def fetch(self, polygon: Polygon) -> tuple[list[WalkNodeRow], list[WalkEdgeRow]]: ...


def _convert_osmnx_graph(graph) -> tuple[list[WalkNodeRow], list[WalkEdgeRow]]:
    nodes = [
        WalkNodeRow(id=node_id, lon=data["x"], lat=data["y"])
        for node_id, data in graph.nodes(data=True)
    ]
    # OSMnx exposes a MultiDiGraph: parallel ways can share the same u/v pair,
    # while our persisted routing edge key is intentionally one directional
    # pair. Retain its shortest traversable length for routing.
    shortest_edges: dict[tuple[int, int], float] = {}
    for u, v, data in graph.edges(data=True):
        key = (u, v)
        shortest_edges[key] = min(shortest_edges.get(key, float("inf")), float(data["length"]))
    edges = [WalkEdgeRow(u=u, v=v, length_m=length) for (u, v), length in shortest_edges.items()]
    return nodes, edges


class OsmnxWalkNetworkFetcher:
    """Fetches the pedestrian network for a polygon via OSMnx (hits the Overpass API).

    Manually verified against the real Overpass API (a small Malioboro-area
    polygon returned 45 nodes / 104 edges in ~7s) — not exercised by the
    automated test suite, since a live external API call doesn't belong in a
    pytest run that needs to stay fast and non-flaky on every commit.
    FakeWalkNetworkFetcher below is what tests use.
    """

    async def fetch(self, polygon: Polygon) -> tuple[list[WalkNodeRow], list[WalkEdgeRow]]:
        import osmnx as ox

        graph = await asyncio.to_thread(ox.graph_from_polygon, polygon, network_type="walk")
        return _convert_osmnx_graph(graph)


class FakeWalkNetworkFetcher:
    def __init__(self, nodes: list[WalkNodeRow], edges: list[WalkEdgeRow]) -> None:
        self._nodes = nodes
        self._edges = edges

    async def fetch(self, polygon: Polygon) -> tuple[list[WalkNodeRow], list[WalkEdgeRow]]:
        return self._nodes, self._edges
