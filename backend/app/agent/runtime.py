import httpx
import networkx as nx
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


class AgentRuntime:
    """Wires the five tools and the LangGraph loop to real routing/data dependencies.

    No routing graph is built from real Yogyakarta data yet (blocked on the
    survey/digitization handoff, TEAM_WORKFLOW.md §4) — an empty graph makes
    route/multistop tools fail through the same typed-error path as a graph
    that failed to load, matching ARCHITECTURE.md §13's degrade-don't-fail
    failure mode rather than needing a special case.
    """

    def __init__(
        self, settings: Settings, engine: AsyncEngine, http_client: httpx.AsyncClient, cache
    ) -> None:
        self.llm: BaseChatModel | None = self._build_llm(settings)
        geocode_resolver = GeocodeResolver(http_client, cache)
        graph_provider = lambda: nx.MultiDiGraph()  # noqa: E731
        coords_provider = lambda: {}  # noqa: E731
        factors_provider = lambda: {}  # noqa: E731

        self.tools: list[BaseTool] = [
            make_toggle_layer_tool(),
            make_get_data_in_viewport_tool(lambda: session_scope(engine)),
            make_calculate_route_tool(graph_provider, coords_provider, geocode_resolver),
            make_plan_multistop_tool(graph_provider, coords_provider, geocode_resolver),
            make_calculate_carbon_savings_tool(factors_provider),
        ]
        self.graph: CompiledStateGraph | None = (
            build_agent_graph(self.llm, self.tools) if self.llm is not None else None
        )

    @staticmethod
    def _build_llm(settings: Settings) -> BaseChatModel | None:
        try:
            return get_llm(settings)
        except UnsupportedLLMProviderError:
            return None


def make_redis_client(redis_url: str) -> redis.Redis:
    return redis.from_url(redis_url)
