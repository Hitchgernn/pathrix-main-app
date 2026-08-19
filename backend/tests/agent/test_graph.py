from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agent.graph import MAX_TOOL_ROUNDS, build_agent_graph
from app.agent.tools import make_toggle_layer_tool
from app.models.agent import Viewport
from app.models.geo import BBox, Coord


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


def _initial_state():
    return {
        "messages": [HumanMessage(content="turn on the transjogja layer")],
        "viewport": Viewport(
            bbox=BBox(min_lon=110.3, min_lat=-7.85, max_lon=110.4, max_lat=-7.75),
            zoom=14,
            center=Coord(lat=-7.8, lon=110.35),
        ),
        "active_layers": set(),
        "last_route": None,
        "ui_commands": [],
        "locale": "id",
    }


async def test_agent_runs_a_tool_then_narrates_and_emits_ui_command():
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

    result = await graph.ainvoke(_initial_state())

    assert result["messages"][-1].content == "TransJogja layer is now on."
    assert len(result["ui_commands"]) == 1
    assert result["ui_commands"][0].action == "toggle_layer"
    assert result["ui_commands"][0].payload == {"layer_id": "transjogja", "on": True}


async def test_agent_handles_unknown_tool_gracefully():
    llm = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "not_a_real_tool", "args": {}, "id": "call1"}],
            ),
            AIMessage(content="Sorry, I could not do that."),
        ]
    )
    graph = build_agent_graph(llm, [make_toggle_layer_tool()])

    result = await graph.ainvoke(_initial_state())

    tool_message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_message.status == "error"
    assert result["messages"][-1].content == "Sorry, I could not do that."


async def test_agent_stops_looping_after_the_tool_round_budget():
    def _tool_call_response(round_num: int) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "toggle_layer",
                    "args": {"layer_id": "x", "on": True},
                    "id": f"call{round_num}",
                }
            ],
        )

    # Always returns a tool call — the graph must still terminate via the round budget.
    llm = ScriptedChatModel(responses=[_tool_call_response(i) for i in range(MAX_TOOL_ROUNDS + 5)])
    graph = build_agent_graph(llm, [make_toggle_layer_tool()])

    result = await graph.ainvoke(_initial_state(), config={"recursion_limit": 100})

    tool_message_count = sum(1 for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_message_count == MAX_TOOL_ROUNDS
