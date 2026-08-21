import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.ui_commands import command_for_tool
from app.models.agent import AgentState
from app.models.routing import CarbonResult, Route

MAX_TOOL_ROUNDS = 5  # per-turn tool-call budget, ARCHITECTURE.md §8.4/§12


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
        return {}

    graph = StateGraph(AgentState)
    graph.add_node("plan", plan)
    graph.add_node("tools", run_tools)
    graph.add_node("respond", respond)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", has_tool_calls, {"tools": "tools", "respond": "respond"})
    graph.add_edge("tools", "plan")
    graph.add_edge("respond", END)

    return graph.compile()
