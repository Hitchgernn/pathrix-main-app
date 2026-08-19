from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agent.graph import build_agent_graph
from app.agent.tools import make_toggle_layer_tool
from app.main import app

_VIEWPORT = {
    "bbox": {"min_lon": 110.3, "min_lat": -7.85, "max_lon": 110.4, "max_lat": -7.75},
    "zoom": 14,
}


class ScriptedChatModel(BaseChatModel):
    responses: list
    call_count: int = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        response = self.responses[self.call_count]
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "scripted"


class _FakeRuntime:
    def __init__(self, graph) -> None:
        self.graph = graph


class _FailingGraph:
    async def ainvoke(self, state):
        raise RuntimeError("boom")


def test_lifespan_builds_a_runtime_with_no_llm_configured():
    with TestClient(app) as client:
        assert client.app.state.runtime.graph is None


def test_user_message_without_llm_returns_llm_unavailable_error():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_message", "text": "hi", "viewport": _VIEWPORT})
        response = ws.receive_json()
        assert response == {
            "type": "error",
            "code": "llm_unavailable",
            "message": "Chat is unavailable right now.",
        }


def test_invalid_message_returns_error_and_keeps_the_connection_open():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "bogus"})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "invalid_message"

        ws.send_json({"type": "viewport_changed", **_VIEWPORT})
        ws.send_json({"type": "user_message", "text": "hi", "viewport": _VIEWPORT})
        response = ws.receive_json()
        assert response["code"] == "llm_unavailable"


def test_full_turn_streams_token_then_ui_command_then_done():
    llm = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "toggle_layer",
                        "args": {"layer_id": "transjogja", "on": True},
                        "id": "call1",
                    }
                ],
            ),
            AIMessage(content="TransJogja layer is now on."),
        ]
    )
    graph = build_agent_graph(llm, [make_toggle_layer_tool()])

    with TestClient(app) as client:
        client.app.state.runtime = _FakeRuntime(graph)
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "user_message",
                    "text": "turn on the transjogja layer",
                    "viewport": _VIEWPORT,
                }
            )
            token_msg = ws.receive_json()
            ui_command_msg = ws.receive_json()
            done_msg = ws.receive_json()

    assert token_msg == {"type": "token", "delta": "TransJogja layer is now on."}
    assert ui_command_msg == {
        "type": "ui_command",
        "action": "toggle_layer",
        "payload": {"layer_id": "transjogja", "on": True},
    }
    assert done_msg == {"type": "done", "route": None, "carbon": None}


def test_agent_error_is_reported_not_raised():
    with TestClient(app) as client:
        client.app.state.runtime = _FakeRuntime(_FailingGraph())
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "user_message", "text": "hi", "viewport": _VIEWPORT})
            response = ws.receive_json()

    assert response["type"] == "error"
    assert response["code"] == "agent_error"
