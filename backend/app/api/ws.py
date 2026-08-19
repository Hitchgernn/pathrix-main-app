from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from pydantic import TypeAdapter, ValidationError

from app.agent.runtime import AgentRuntime
from app.models.agent import AgentState, Viewport
from app.models.geo import BBox, Coord
from app.models.ws import (
    DoneOut,
    ErrorOut,
    TokenOut,
    UICommandOut,
    ViewportChangedIn,
    WSClientMessage,
)

router = APIRouter()

_client_message_adapter = TypeAdapter(WSClientMessage)


def _bbox_center(bbox: BBox) -> Coord:
    return Coord(lat=(bbox.min_lat + bbox.max_lat) / 2, lon=(bbox.min_lon + bbox.max_lon) / 2)


def _init_state(viewport: Viewport) -> AgentState:
    return {
        "messages": [],
        "viewport": viewport,
        "active_layers": set(),
        "last_route": None,
        "ui_commands": [],
        "locale": "id",
    }


def _with_viewport(state: AgentState | None, bbox: BBox, zoom: float) -> AgentState:
    viewport = Viewport(bbox=bbox, zoom=zoom, center=_bbox_center(bbox))
    if state is None:
        return _init_state(viewport)
    state["viewport"] = viewport
    return state


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    runtime: AgentRuntime = websocket.app.state.runtime
    await websocket.accept()
    state: AgentState | None = None

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                message = _client_message_adapter.validate_python(raw)
            except ValidationError as exc:
                await websocket.send_json(
                    ErrorOut(code="invalid_message", message=str(exc)).model_dump()
                )
                continue

            if isinstance(message, ViewportChangedIn):
                state = _with_viewport(state, message.bbox, message.zoom)
                continue

            state = _with_viewport(state, message.viewport.bbox, message.viewport.zoom)
            state["messages"].append(HumanMessage(content=message.text))

            if runtime.graph is None:
                await websocket.send_json(
                    ErrorOut(
                        code="llm_unavailable", message="Chat is unavailable right now."
                    ).model_dump()
                )
                continue

            try:
                result = await runtime.graph.ainvoke(state)
            except Exception as exc:
                await websocket.send_json(
                    ErrorOut(code="agent_error", message=str(exc)).model_dump()
                )
                continue

            final_text = result["messages"][-1].content
            await websocket.send_json(TokenOut(delta=final_text).model_dump())
            for command in result["ui_commands"]:
                await websocket.send_json(
                    UICommandOut(action=command.action, payload=command.payload).model_dump()
                )
            await websocket.send_json(DoneOut().model_dump())

            state = {**result, "ui_commands": []}
    except WebSocketDisconnect:
        return
