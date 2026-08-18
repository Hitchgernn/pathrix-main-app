import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import settings
from app.models.health import ComponentStatus, HealthStatus

router = APIRouter(prefix="/api")


async def _check_db() -> ComponentStatus:
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return "ok"
    except Exception:
        return "down"


async def _check_redis() -> ComponentStatus:
    try:
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception:
        return "down"


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    db_status = await _check_db()
    redis_status = await _check_redis()
    return HealthStatus(db=db_status, redis=redis_status, graph_loaded=False)
