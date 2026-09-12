import httpx
import pytest
from shapely import Polygon

from app.data.mapid import FakeMapidClient, HttpMapidClient, MapidApiError
from app.models.mapid import Feature, LayerFeatures, MissionPage

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


_HALTE_PAYLOAD = {
    "layer_id": "6aa40d79753cb27abe0473e5",
    "layer_name": "HALTE DI KOTA YOGYAKARTA TAHUN 2025",
    "type": "FeatureCollection",
    "fields": [{"key": "k", "name": "NAMA", "type": "text"}],
    "features": [
        {
            "id": "f1e2d3c4",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [110.3917757, -7.8340699]},
            "properties": {"fid": 547, "NAMA": "TRANS JOGJA TERMINAL GIWANGAN"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [110.36, -7.79]},
            "properties": {"fid": 548, "NAMA": "MALIOBORO 1"},
        },
    ],
}


async def test_fetch_layer_normalizes_a_geoserver_feature_collection():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=_HALTE_PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = HttpMapidClient(api_key="mission", http_client=http, geoserver_api_key="geo")
        layer = await client.fetch_layer("6aa40d79753cb27abe0473e5", "6aa40ac8753cb27abe032542")

    # The geoserver takes its own key, not the mission key.
    assert captured["api_key"] == "geo"
    assert captured["layer_id"] == "6aa40d79753cb27abe0473e5"
    assert captured["project_id"] == "6aa40ac8753cb27abe032542"

    assert layer.layer_name == "HALTE DI KOTA YOGYAKARTA TAHUN 2025"
    assert layer.features[0].external_id == "f1e2d3c4"
    assert layer.features[0].properties["NAMA"] == "TRANS JOGJA TERMINAL GIWANGAN"
    # No per-feature uuid: fall back to the layer-namespaced source row number.
    assert layer.features[1].external_id == "6aa40d79753cb27abe0473e5:548"


async def test_fetch_layer_rejects_a_response_without_features():
    payload = {"success": False, "message": "layer not found"}
    async with _client_with_response(payload) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        with pytest.raises(MapidApiError, match="layer not found"):
            await client.fetch_layer("missing", "project")


async def test_geoserver_key_falls_back_to_the_mission_key():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=_HALTE_PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = HttpMapidClient(api_key="only-one", http_client=http)
        await client.fetch_layer("l", "p")

    assert captured["api_key"] == "only-one"


async def test_fake_client_serves_layers_and_defaults_to_empty():
    fake = FakeMapidClient(
        {},
        layers={
            "halte": LayerFeatures(
                layer_id="halte",
                layer_name="Halte",
                features=[
                    Feature(
                        external_id="h1",
                        properties={"NAMA": "HALTE A"},
                        geometry={"type": "Point", "coordinates": [110.37, -7.8]},
                    )
                ],
            )
        },
    )
    assert (await fake.fetch_layer("halte", "p")).features[0].external_id == "h1"
    assert (await fake.fetch_layer("nope", "p")).features == []


async def test_fetch_layer_list_normalizes_a_project_catalogue():
    payload = [
        {
            "_id": "6aa40d79753cb27abe0473e5",
            "name": "HALTE DI KOTA YOGYAKARTA TAHUN 2025",
            "type": "Point",
            "fields": [{"name": "NAMA"}, {"name": "ALAMAT"}],
        },
        {"_id": "6aa40d7e753cb27abe047532", "name": "HALTE ... TAHUN 2024", "type": "Point"},
    ]
    async with _client_with_response(payload) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        layers = await client.fetch_layer_list("project-1")

    assert [layer.layer_id for layer in layers] == [
        "6aa40d79753cb27abe0473e5",
        "6aa40d7e753cb27abe047532",
    ]
    assert layers[0].fields == ["NAMA", "ALAMAT"]
    # A layer with no field list is a layer with no field list, not a crash.
    assert layers[1].fields == []


async def test_fetch_layer_list_rejects_a_non_list_payload():
    async with _client_with_response({"success": False, "message": "nope"}) as http:
        client = HttpMapidClient(api_key="k", http_client=http)
        with pytest.raises(MapidApiError):
            await client.fetch_layer_list("project-1")
