from app.agent.ui_commands import command_for_tool
from app.models.agent import LayerResult
from app.models.network import NetworkData, RouteRow, RouteStopRow, StopRow
from app.routing.build import build_graph_from_network, stop_node
from app.routing.shortest_path import calculate_route


def test_toggle_layer_result_becomes_a_toggle_layer_command():
    command = command_for_tool("toggle_layer", LayerResult(layer_id="transit", on=True))
    assert command is not None
    assert command.action == "toggle_layer"
    assert command.payload == {"layer_id": "transit", "on": True}


def test_draw_route_payload_carries_coordinates_the_client_can_draw():
    network = NetworkData(
        stops=[StopRow(id=1, lon=110.30, lat=-7.80), StopRow(id=2, lon=110.35, lat=-7.82)],
        routes=[RouteRow(id=10, headway_min=10, fare_idr=3500)],
        route_stops=[
            RouteStopRow(route_id=10, stop_id=1, seq=0, travel_time_from_prev_s=None),
            RouteStopRow(route_id=10, stop_id=2, seq=1, travel_time_from_prev_s=600),
        ],
        pangkalan=[],
    )
    graph, _ = build_graph_from_network(network)
    route = calculate_route(graph, stop_node(1), stop_node(2), "tercepat")

    command = command_for_tool("calculate_route", route)

    assert command is not None
    assert command.action == "draw_route"
    # The client builds its GeoJSON from these; without them it draws nothing.
    assert all(len(leg["coordinates"]) == 2 for leg in command.payload["legs"])


def test_a_tool_with_no_map_effect_produces_no_command():
    assert command_for_tool("calculate_carbon_savings", LayerResult(layer_id="x", on=True)) is None
