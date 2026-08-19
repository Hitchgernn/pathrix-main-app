from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.runtime import make_redis_client
from app.api.ratelimit import RateLimitMiddleware
from app.config import settings


def test_requests_beyond_the_limit_get_429():
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        cache = make_redis_client(settings.redis_url)
        await cache.delete("ratelimit:testclient")
        app.state.cache = cache
        yield
        await cache.aclose()

    test_app = FastAPI(lifespan=lifespan)
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

    @test_app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(test_app) as client:
        statuses = [client.get("/ping").status_code for _ in range(5)]

    assert statuses == [200, 200, 200, 429, 429]


def test_fails_open_when_redis_is_unreachable():
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.cache = redis.from_url("redis://localhost:1/0", socket_connect_timeout=1)
        yield

    test_app = FastAPI(lifespan=lifespan)
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

    @test_app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(test_app) as client:
        response = client.get("/ping")

    assert response.status_code == 200
