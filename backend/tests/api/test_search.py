import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert

from app.data.geocode import GeocodeResolver
from app.data.repository import search_places, upsert_poi
from app.data.schema import TransitStop
from app.main import app
from app.models.mapid import Feature


class _MemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._values[key] = value


def _nominatim_client(payload: list[dict]) -> httpx.AsyncClient:
    """Nominatim is never called for real in the suite — same rule as
    OsmnxWalkNetworkFetcher: an external API would make CI flaky."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_geocode_rejects_an_empty_query():
    with TestClient(app) as client:
        response = client.get("/api/geocode", params={"q": ""})
    assert response.status_code == 422


async def test_geocode_search_returns_normalized_hits():
    async with _nominatim_client(
        [
            {
                "place_id": 42,
                "display_name": "Malioboro, Gedongtengen, Yogyakarta",
                "lon": "110.3656",
                "lat": "-7.7935",
            }
        ]
    ) as http_client:
        resolver = GeocodeResolver(http_client, _MemoryCache())
        hits = await resolver.search("malioboro", 5)

    assert len(hits) == 1
    assert hits[0].name == "Malioboro"
    assert hits[0].kind == "address"
    assert hits[0].id == "address:42"


async def test_geocode_search_is_cached():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json=[
                {"place_id": 1, "display_name": "Tugu, Yogyakarta", "lon": "110.3", "lat": "-7.7"}
            ],
        )

    cache = _MemoryCache()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        resolver = GeocodeResolver(http_client, cache)
        await resolver.search("tugu", 5)
        await resolver.search("tugu", 5)

    assert calls == 1


async def test_search_places_finds_a_seeded_stop(db_session):
    await db_session.execute(
        insert(TransitStop).values(
            external_id="searchstop1",
            name="Halte Malioboro 1",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.3656, -7.7935), 4326),
            source="test",
        )
    )
    await db_session.flush()

    hits = await search_places(db_session, "malioboro")

    assert any(hit.name == "Halte Malioboro 1" and hit.kind == "transit" for hit in hits)


async def test_search_places_ranks_transit_above_mission_rows(db_session):
    await db_session.execute(
        insert(TransitStop).values(
            external_id="searchstop2",
            name="Halte Prambanan",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.49, -7.75), 4326),
            source="test",
        )
    )
    await upsert_poi(
        db_session,
        [
            Feature(
                external_id="searchpoi1",
                properties={"nama_tempat": "Warung Prambanan"},
                geometry={"type": "Point", "coordinates": [110.49, -7.75]},
            )
        ],
        "menugo",
    )

    hits = await search_places(db_session, "prambanan")

    kinds = [hit.kind for hit in hits]
    assert kinds.index("transit") < kinds.index("poi")


async def test_search_places_ignores_a_blank_query(db_session):
    assert await search_places(db_session, "   ") == []


@pytest.mark.parametrize("limit", [1, 3])
async def test_search_places_respects_the_limit(db_session, limit):
    await upsert_poi(
        db_session,
        [
            Feature(
                external_id=f"limitpoi{index}",
                properties={"nama_tempat": f"Angkringan Limit {index}"},
                geometry={"type": "Point", "coordinates": [110.37, -7.80]},
            )
            for index in range(5)
        ],
        "menugo",
    )

    hits = await search_places(db_session, "Angkringan Limit", limit)

    assert len(hits) <= limit
