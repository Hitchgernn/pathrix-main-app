from pydantic import BaseModel

from app.models.agent import LayerResult, UICommand
from app.models.routing import Route


def command_for_tool(tool_name: str, result: BaseModel) -> UICommand | None:
    if tool_name == "toggle_layer" and isinstance(result, LayerResult):
        return UICommand(
            action="toggle_layer", payload={"layer_id": result.layer_id, "on": result.on}
        )
    if tool_name == "calculate_route" and isinstance(result, Route):
        return UICommand(action="draw_route", payload=result.model_dump())
    return None
