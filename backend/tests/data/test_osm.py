import networkx as nx

from app.data.osm import FakeWalkNetworkFetcher, _convert_osmnx_graph
from app.models.network import WalkEdgeRow, WalkNodeRow


def test_convert_osmnx_graph_extracts_nodes_and_edges():
    g = nx.MultiDiGraph()
    g.add_node(1, x=110.30, y=-7.80)
    g.add_node(2, x=110.31, y=-7.81)
    g.add_edge(1, 2, length=120.5)

    nodes, edges = _convert_osmnx_graph(g)

    assert nodes == [
        WalkNodeRow(id=1, lon=110.30, lat=-7.80),
        WalkNodeRow(id=2, lon=110.31, lat=-7.81),
    ]
    assert edges == [WalkEdgeRow(u=1, v=2, length_m=120.5)]


async def test_fake_fetcher_returns_canned_data_regardless_of_polygon():
    nodes = [WalkNodeRow(id=1, lon=110.30, lat=-7.80)]
    edges = [WalkEdgeRow(u=1, v=1, length_m=0.0)]
    fetcher = FakeWalkNetworkFetcher(nodes, edges)

    result_nodes, result_edges = await fetcher.fetch(polygon=None)
    assert result_nodes == nodes
    assert result_edges == edges
