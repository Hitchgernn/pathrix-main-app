from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.models.agent import UICommandAction
from app.models.geo import BBox
from app.models.routing import CarbonResult, Route


class ViewportPayload(BaseModel):
    bbox: BBox
    zoom: float


class UserMessageIn(BaseModel):
    type: Literal["user_message"] = "user_message"
    text: str
    viewport: ViewportPayload


class ViewportChangedIn(BaseModel):
    type: Literal["viewport_changed"] = "viewport_changed"
    bbox: BBox
    zoom: float


WSClientMessage = Annotated[UserMessageIn | ViewportChangedIn, Field(discriminator="type")]


class TokenOut(BaseModel):
    type: Literal["token"] = "token"
    delta: str


class UICommandOut(BaseModel):
    type: Literal["ui_command"] = "ui_command"
    action: UICommandAction
    payload: dict


class DoneOut(BaseModel):
    type: Literal["done"] = "done"
    route: Route | None = None
    carbon: CarbonResult | None = None


class ErrorOut(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
