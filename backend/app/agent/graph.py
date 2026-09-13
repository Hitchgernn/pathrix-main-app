import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.ui_commands import command_for_tool
from app.models.agent import AgentState
from app.models.routing import CarbonResult, Route

MAX_TOOL_ROUNDS = 8  # per-turn tool-call budget, ARCHITECTURE.md §8.4/§12
# 5 undercounted a real LLM: the last-mile choreography alone (calculate_route
# -> get_data_in_viewport -> calculate_route again -> calculate_carbon_savings)
# is already 4 sequential, non-batchable tool calls, leaving no slack for a
# real model's occasional extra call. (The actual cause of a much longer
# observed loop was the emission_factors table being empty on a fresh
# deploy — every calculate_carbon_savings call errored and the model kept
# retrying it; fixed by seeding that table, not by the round budget.)

# Hitting the round budget can land on a message that is itself an unexecuted
# tool call (empty .content) — ws.py sends this text straight to the user, so
# without this fallback a cut-off turn shows up as a silent, empty reply.
# Keyed by AgentState's locale so it matches whichever language the rest of
# the turn was in, rather than always breaking into English mid-conversation.
ROUND_BUDGET_FALLBACK = {
    "id": (
        "Aku butuh lebih banyak langkah dari yang diizinkan untuk menyelesaikan "
        "permintaan ini. Coba tanya dengan nama halte/tempat yang lebih spesifik, "
        "atau tanya lagi."
    ),
    "en": (
        "I needed more steps than I'm allowed to finish this request. "
        "Try asking with a more specific stop or place name, or ask again."
    ),
}


# Belt-and-suspenders companion to SYSTEM_PROMPT's plain-text instruction —
# prompt compliance is probabilistic, this is deterministic. Strips emoji,
# markdown emphasis/heading/quote markers, and bullet prefixes the model
# still occasionally emits.
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"  # symbols, pictographs, emoticons, transport, supplemental
    "\U00002600-\U000027bf"  # misc symbols and dingbats
    "\U0001f1e6-\U0001f1ff"  # regional indicators (flag emoji)
    "\U00002b00-\U00002bff"  # misc symbols and arrows
    "\U0000fe0f"  # emoji presentation selector
    "]+"
)
_BULLET_PREFIX_RE = re.compile(r"^[ \t]*[-*•][ \t]+", flags=re.MULTILINE)
_MARKDOWN_MARKUP_RE = re.compile(r"[*_`#>~]+")


def _clean_reply(text: str) -> str:
    cleaned = _EMOJI_RE.sub("", text)
    cleaned = _BULLET_PREFIX_RE.sub("", cleaned)
    cleaned = _MARKDOWN_MARKUP_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _serialize(result: object) -> str:
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, list) and all(isinstance(item, BaseModel) for item in result):
        return json.dumps([item.model_dump() for item in result])
    return json.dumps(result)


def build_agent_graph(llm: BaseChatModel, tools: list[BaseTool]) -> CompiledStateGraph:
    bound_llm = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    def plan(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = bound_llm.invoke(messages)
        return {"messages": [response]}

    def has_tool_calls(state: AgentState) -> str:
        last = state["messages"][-1]
        rounds_so_far = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
        if getattr(last, "tool_calls", None) and rounds_so_far < MAX_TOOL_ROUNDS:
            return "tools"
        return "respond"

    async def run_tools(state: AgentState) -> dict:
        last = state["messages"][-1]
        tool_messages = []
        new_commands = []
        last_route = None
        last_carbon = None
        for call in last.tool_calls:
            selected = tools_by_name.get(call["name"])
            if selected is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"error: unknown tool {call['name']!r}",
                        tool_call_id=call["id"],
                        name=call["name"],
                        status="error",
                    )
                )
                continue
            try:
                result = await selected.ainvoke(call["args"])
                tool_messages.append(
                    ToolMessage(
                        content=_serialize(result), tool_call_id=call["id"], name=call["name"]
                    )
                )
                command = (
                    command_for_tool(call["name"], result)
                    if isinstance(result, BaseModel)
                    else None
                )
                if command is not None:
                    new_commands.append(command)
                if isinstance(result, Route):
                    last_route = result
                elif isinstance(result, CarbonResult):
                    last_carbon = result
            except Exception as exc:
                tool_messages.append(
                    ToolMessage(
                        content=f"error: {exc}",
                        tool_call_id=call["id"],
                        name=call["name"],
                        status="error",
                    )
                )

        update = {"messages": tool_messages, "ui_commands": state["ui_commands"] + new_commands}
        if last_route is not None:
            update["last_route"] = last_route
        if last_carbon is not None:
            update["last_carbon"] = last_carbon
        return update

    def respond(state: AgentState) -> dict:
        last = state["messages"][-1]
        if not (last.content or "").strip():
            fallback = ROUND_BUDGET_FALLBACK.get(state["locale"], ROUND_BUDGET_FALLBACK["en"])
            return {"messages": [AIMessage(content=fallback)]}
        cleaned = _clean_reply(last.content)
        if cleaned == last.content or not cleaned:
            return {}
        return {"messages": [AIMessage(content=cleaned)]}

    graph = StateGraph(AgentState)
    graph.add_node("plan", plan)
    graph.add_node("tools", run_tools)
    graph.add_node("respond", respond)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", has_tool_calls, {"tools": "tools", "respond": "respond"})
    graph.add_edge("tools", "plan")
    graph.add_edge("respond", END)

    return graph.compile()
