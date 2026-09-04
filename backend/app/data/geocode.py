import json
from typing import Protocol

import httpx

from app.models.geo import Coord
from app.models.search import PlaceHit

NOMINATIM_BASE_URL = "https://nominatim.mapid.io"
CACHE_TTL_S = 60 * 60 * 24 * 7  # days, per ARCHITECTURE.md §11.2 — place names are stable

# The product only routes inside the Yogyakarta special region, so an unbiased
# search that answers "Malioboro" with a street in Surabaya is a wrong answer,
# not a broader one. Nominatim takes the window as left,top,right,bottom.
YOGYA_VIEWBOX = "110.00,-7.50,110.95,-8.25"


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

    async def search(self, query: str, limit: int = 5) -> list[PlaceHit]:
        """Several candidates for a search box, where `forward` returns one coord.

        Cached under its own key so it never collides with `forward`'s
        single-coord entries, on the same TTL — a place name's coordinates are
        just as stable whether one or five were asked for.
        """
        cache_key = f"geosearch:{_normalize(query)}:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            cached_str = cached.decode() if isinstance(cached, bytes) else cached
            return [PlaceHit(**hit) for hit in json.loads(cached_str)]

        response = await self._http_client.get(
            f"{NOMINATIM_BASE_URL}/search",
            params={
                "q": query,
                "format": "json",
                "limit": limit,
                "viewbox": YOGYA_VIEWBOX,
                "bounded": 1,
            },
        )
        response.raise_for_status()
        hits = [
            PlaceHit(
                id=f"address:{result.get('place_id', index)}",
                name=str(result["display_name"]).split(",")[0].strip(),
                kind="address",
                subtitle=str(result["display_name"]),
                lon=float(result["lon"]),
                lat=float(result["lat"]),
            )
            for index, result in enumerate(response.json())
        ]
        await self._cache.set(
            cache_key, json.dumps([hit.model_dump() for hit in hits]), ex=CACHE_TTL_S
        )
        return hits

    async def reverse(self, lat: float, lon: float) -> str | None:
        response = await self._http_client.get(
            f"{NOMINATIM_BASE_URL}/reverse", params={"lat": lat, "lon": lon, "format": "json"}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("display_name")
