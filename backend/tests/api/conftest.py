from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import make_redis_client
from app.api.deps import get_session
from app.config import settings
from app.data.db import init_db, make_engine, session_scope
from app.main import app
from tests.conftest import TEST_DATABASE_URL, ensure_test_database


@pytest.fixture(autouse=True)
async def _api_reads_the_test_database() -> AsyncIterator[None]:
    """Point the app's session dependency at the same database `db_session` seeds.

    The app otherwise builds its engine from `settings.database_url` in
    `main.lifespan`, which is the *dev* database — a test that seeds a row and
    then asks the API for it would be reading a different Postgres than it
    wrote to.
    """
    try:
        await ensure_test_database()
    except Exception as exc:
        pytest.skip(f"PostGIS not reachable for the API tests: {exc}")

    engine = make_engine(TEST_DATABASE_URL)
    await init_db(engine)
    # TestClient runs application code on another event loop/thread. Drop the
    # connection opened by init_db so its pool cannot cross loop boundaries.
    await engine.dispose()

    async def _get_test_session() -> AsyncIterator[AsyncSession]:
        async with session_scope(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_test_session
    yield
    app.dependency_overrides.pop(get_session, None)
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _reset_shared_rate_limit_key():
    cache = make_redis_client(settings.redis_url)
    await cache.delete("ratelimit:testclient")
    yield
    await cache.aclose()
