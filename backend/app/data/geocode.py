from typing import Protocol

import httpx

from app.models.geo import Coord

NOMINATIM_BASE_URL = "https://nominatim.mapid.io"
CACHE_TTL_S = 60 * 60 * 24 * 7  # days, per ARCHITECTURE.md §11.2 — place names are stable


class CacheLike(Protocol):
    async def get(self, key: str) -> bytes | str | None: ...
    async def set(self, key: str, value: str, ex: int | None = None) -> None: ...


def _normalize(query: str) -> str:
    return query.strip().lower()


class GeocodeResolver:
    def __init__(self, http_client: httpx.AsyncClient, cache: CacheLike) -> None:
        self._http_client = http_client
        self._cache = cache

    async def forward(self, query: str) -> Coord | None:
        cache_key = f"geocode:{_normalize(query)}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            cached_str = cached.decode() if isinstance(cached, bytes) else cached
            lat_str, lon_str = cached_str.split(",")
            return Coord(lat=float(lat_str), lon=float(lon_str))

        response = await self._http_client.get(
            f"{NOMINATIM_BASE_URL}/search", params={"q": query, "format": "json"}
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None

        coord = Coord(lat=float(results[0]["lat"]), lon=float(results[0]["lon"]))
        await self._cache.set(cache_key, f"{coord.lat},{coord.lon}", ex=CACHE_TTL_S)
        return coord

    async def reverse(self, lat: float, lon: float) -> str | None:
        response = await self._http_client.get(
            f"{NOMINATIM_BASE_URL}/reverse", params={"lat": lat, "lon": lon, "format": "json"}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("display_name")
