from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.agent.runtime import AgentRuntime, make_redis_client
from app.api.layers import router as layers_router
from app.api.ratelimit import RateLimitMiddleware
from app.api.routes import router as http_router
from app.api.ws import router as ws_router
from app.config import settings
from app.data.db import make_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    http_client = httpx.AsyncClient()
    cache = make_redis_client(settings.redis_url)

    app.state.engine = engine
    app.state.cache = cache
    app.state.runtime = await AgentRuntime.create(settings, engine, http_client, cache)

    yield

    await engine.dispose()
    await http_client.aclose()
    await cache.aclose()


app = FastAPI(title="PATHRIX API", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.include_router(http_router)
app.include_router(layers_router)
app.include_router(ws_router)
