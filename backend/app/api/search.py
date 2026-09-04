import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_geocoder, get_session
from app.data.geocode import GeocodeResolver
from app.data.repository import search_places
from app.models.search import PlaceHit

router = APIRouter(prefix="/api")


@router.get("/geocode", response_model=list[PlaceHit])
async def geocode(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
    geocoder: GeocodeResolver = Depends(get_geocoder),
) -> list[PlaceHit]:
    """Search box behind Explore and Home.

    Mirrored rows rank above geocoded addresses: a halte we actually hold data
    for is a better answer than a street Nominatim happens to name similarly.
    Nominatim only fills whatever slots are left, and a failure there degrades
    to DB-only results — a slow or down third party must never turn the app's
    search box into an error state (ARCHITECTURE.md §13).
    """
    local = await search_places(session, q, limit)
    remaining = limit - len(local)
    if remaining <= 0:
        return local

    try:
        remote = await geocoder.search(q, remaining)
    except (httpx.HTTPError, ValueError, KeyError):
        return local

    seen = {hit.id for hit in local}
    return local + [hit for hit in remote if hit.id not in seen][:remaining]
