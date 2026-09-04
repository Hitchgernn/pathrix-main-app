from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db import session_scope
from app.data.geocode import GeocodeResolver


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with session_scope(request.app.state.engine) as session:
        yield session


def get_geocoder(request: Request) -> GeocodeResolver:
    """The shared httpx client and Redis connection are created once in
    `main.lifespan`; a per-request resolver would drop the geocode cache."""
    return GeocodeResolver(request.app.state.http_client, request.app.state.cache)
