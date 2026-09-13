from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.data.schema import Base


def make_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or settings.database_url)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.run_sync(Base.metadata.create_all)
        # ``create_all`` does not widen columns in an existing local dev DB.
        # This additive PostgreSQL migration preserves existing OSM ids/edges,
        # while allowing current OSM node ids beyond signed int32.
        await conn.exec_driver_sql("ALTER TABLE walk_nodes ALTER COLUMN id TYPE BIGINT")
        await conn.exec_driver_sql("ALTER TABLE walk_edges ALTER COLUMN u TYPE BIGINT")
        await conn.exec_driver_sql("ALTER TABLE walk_edges ALTER COLUMN v TYPE BIGINT")


@asynccontextmanager
async def session_scope(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
