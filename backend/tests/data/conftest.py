import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.data.db import init_db, make_engine

TEST_DATABASE_URL = "postgresql+asyncpg://pathrix:pathrix@localhost:5432/pathrix"


@pytest.fixture
async def db_session():
    engine = make_engine(TEST_DATABASE_URL)
    try:
        await init_db(engine)
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostGIS not reachable at {TEST_DATABASE_URL}: {exc}")

    async with engine.begin() as conn:
        await conn.exec_driver_sql("TRUNCATE poi, properti RESTART IDENTITY")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
