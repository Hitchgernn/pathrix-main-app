from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from app.models.geo import BBox, Coord
from app.models.routing import Route

UICommandAction = Literal["toggle_layer", "fly_to", "draw_route", "highlight"]


class UICommand(BaseModel):
    action: UICommandAction
    payload: dict


class Viewport(BaseModel):
    bbox: BBox
    zoom: float
    center: Coord


class LayerResult(BaseModel):
    layer_id: str
    on: bool


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    viewport: Viewport
    active_layers: set[str]
    last_route: Route | None
    ui_commands: list[UICommand]
    locale: str
