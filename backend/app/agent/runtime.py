import httpx
import redis.asyncio as redis
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agent.graph import build_agent_graph
from app.agent.llm import UnsupportedLLMProviderError, get_llm
from app.agent.tools import (
    make_calculate_carbon_savings_tool,
    make_calculate_route_tool,
    make_get_data_in_viewport_tool,
    make_plan_multistop_tool,
    make_toggle_layer_tool,
)
from app.config import Settings
from app.data.db import session_scope
from app.data.geocode import GeocodeResolver
from app.data.repository import fetch_emission_factors, fetch_network_data
from app.routing.build import build_graph_from_network


class AgentRuntime:
    """Wires the five tools and the LangGraph loop to real routing/data dependencies.

    The routing graph is built once at startup from whatever's in the DB
    (ARCHITECTURE.md §4.2 — process-local state), via AgentRuntime.create.
    No OSMnx pedestrian network is wired in yet (ARCHITECTURE.md §7.1's walk
    nodes) — that needs a real OSM fetch over the study area, a separate
    task. An empty DB still produces a valid (empty) graph, so route/
    multistop tools degrade through the same typed-error path either way.
    """

    def __init__(
        self,
        llm: BaseChatModel | None,
        tools: list[BaseTool],
        graph: CompiledStateGraph | None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.graph = graph

    @classmethod
    async def create(
        cls, settings: Settings, engine: AsyncEngine, http_client: httpx.AsyncClient, cache
    ) -> "AgentRuntime":
        llm = cls._build_llm(settings)
        geocode_resolver = GeocodeResolver(http_client, cache)

        async with session_scope(engine) as session:
            network = await fetch_network_data(session)
            factors = await fetch_emission_factors(session)

        routing_graph, coords = build_graph_from_network(network)

        tools: list[BaseTool] = [
            make_toggle_layer_tool(),
            make_get_data_in_viewport_tool(lambda: session_scope(engine)),
            make_calculate_route_tool(lambda: routing_graph, lambda: coords, geocode_resolver),
            make_plan_multistop_tool(lambda: routing_graph, lambda: coords, geocode_resolver),
            make_calculate_carbon_savings_tool(lambda: factors),
        ]
        graph = build_agent_graph(llm, tools) if llm is not None else None
        return cls(llm, tools, graph)

    @staticmethod
    def _build_llm(settings: Settings) -> BaseChatModel | None:
        try:
            return get_llm(settings)
        except UnsupportedLLMProviderError:
            return None


def make_redis_client(redis_url: str) -> redis.Redis:
    return redis.from_url(redis_url)
