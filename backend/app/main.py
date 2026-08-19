from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.agent.runtime import AgentRuntime, make_redis_client
from app.api.routes import router as http_router
from app.api.ws import router as ws_router
from app.config import settings
from app.data.db import make_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    http_client = httpx.AsyncClient()
    cache = make_redis_client(settings.redis_url)

    app.state.runtime = AgentRuntime(settings, engine, http_client, cache)

    yield

    await engine.dispose()
    await http_client.aclose()
    await cache.aclose()


app = FastAPI(title="PATHRIX API", lifespan=lifespan)
app.include_router(http_router)
app.include_router(ws_router)
