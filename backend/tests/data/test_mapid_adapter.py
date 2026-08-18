import httpx
import pytest
from shapely import Polygon

from app.data.mapid import FakeMapidClient, HttpMapidClient, MapidApiError
from app.models.mapid import Feature, MissionPage

_POLYGON = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])


def _client_with_response(json_body: dict) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json_body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_missions_normalizes_menugo_shape():
    payload = {
        "success": True,
        "message": "ok",
        "features": [
            {
                "_id": "m1",
                "properties": {"nama_tempat": "Warung Bu Tini", "jam_buka": "08:00"},
                "geometry": {"type": "Point", "coordinates": [110.37, -7.80]},
            }
        ],
        "pagination": {"total": 1, "limit": 100, "offset": 0, "hasMore": False},
    }
    async with _client_with_response(payload) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        page = await client.fetch_missions("menugo", _POLYGON)

    assert page.has_more is False
    assert page.features[0].external_id == "m1"
    assert page.features[0].properties["nama_tempat"] == "Warung Bu Tini"


async def test_fetch_missions_normalizes_activities_shape():
    payload = {
        "success": True,
        "message": "ok",
        "data": {
            "activities": [
                {
                    "_id": "a1",
                    "title": "Kerja Bakti",
                    "description": "desc",
                    "geometry": {"type": "Point", "coordinates": [110.4, -7.8]},
                    "medias": [],
                    "user_name": "budi",
                    "user_full_name": "Budi S",
                    "community_name": "RW 5",
                }
            ]
        },
    }
    async with _client_with_response(payload) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        page = await client.fetch_missions("activities", _POLYGON)

    assert page.features[0].external_id == "a1"
    assert page.has_more is False


async def test_fetch_missions_raises_on_api_error():
    payload = {"success": False, "message": "feature is required in body"}
    async with _client_with_response(payload) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        with pytest.raises(MapidApiError):
            await client.fetch_missions("menugo", _POLYGON)


def test_basemap_style_url():
    url = HttpMapidClient.basemap_style_url("street-v2.0", "KEY123")
    assert url == "https://v2.basemap.mapid.io/styles/street-v2.0/style.json?key=KEY123"


async def test_fake_mapid_client_returns_fixture_or_empty_page():
    fixture = MissionPage(
        features=[Feature(external_id="x", properties={}, geometry={})], has_more=False
    )
    client = FakeMapidClient({"menugo": fixture})

    page = await client.fetch_missions("menugo", _POLYGON)
    assert page.features[0].external_id == "x"

    empty_page = await client.fetch_missions("struckgo", _POLYGON)
    assert empty_page.features == []
