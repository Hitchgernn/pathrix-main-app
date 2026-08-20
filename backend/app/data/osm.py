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
    edges = [
        WalkEdgeRow(u=u, v=v, length_m=data["length"]) for u, v, data in graph.edges(data=True)
    ]
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
