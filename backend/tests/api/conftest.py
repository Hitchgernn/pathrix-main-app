import pytest

from app.agent.runtime import make_redis_client
from app.config import settings


@pytest.fixture(autouse=True)
async def _reset_shared_rate_limit_key():
    cache = make_redis_client(settings.redis_url)
    await cache.delete("ratelimit:testclient")
    yield
    await cache.aclose()
