import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data.db import init_db, make_engine

# A separate database from the one `uvicorn` reads. The fixture below TRUNCATEs
# every table it touches, so pointing it at the dev database means a test run
# silently destroys whatever was last ETL'd into it — which it did, once.
# Overridable for CI or a remote Postgres.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pathrix:pathrix@localhost:5432/pathrix_test",
)

_MAINTENANCE_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
_TEST_DATABASE_NAME = TEST_DATABASE_URL.rsplit("/", 1)[1]


_provisioned = False


async def ensure_test_database() -> None:
    """CREATE DATABASE if the test database is not there yet.

    Makes the suite self-provisioning: `docker compose up -d db` creates only
    the one database named in the compose file, and a manual `createdb` before
    `pytest` is a step every fresh checkout and CI run would trip over. Runs
    once per session; raises if Postgres is unreachable, and each caller
    decides whether that is a skip.
    """
    global _provisioned
    if _provisioned:
        return

    engine = create_async_engine(_MAINTENANCE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _TEST_DATABASE_NAME},
            )
            if exists.first() is None:
                # Not parameterisable — an identifier, quoted instead.
                await conn.exec_driver_sql(f'CREATE DATABASE "{_TEST_DATABASE_NAME}"')
    finally:
        await engine.dispose()

    _provisioned = True


@pytest.fixture
async def db_session():
    try:
        await ensure_test_database()
    except Exception as exc:
        pytest.skip(f"PostGIS not reachable at {_MAINTENANCE_URL}: {exc}")

    engine = make_engine(TEST_DATABASE_URL)
    try:
        await init_db(engine)
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostGIS not reachable at {TEST_DATABASE_URL}: {exc}")

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "TRUNCATE transit_schedule_imports, poi, properti, isochrones, "
            "transit_stops, transit_routes, "
            "pangkalan, emission_factors, walk_nodes, walk_edges RESTART IDENTITY CASCADE"
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
