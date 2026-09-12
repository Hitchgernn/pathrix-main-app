from datetime import date
from typing import Protocol

import httpx
from shapely import Polygon
from shapely.geometry import mapping

from app.models.mapid import Dataset, Feature, LayerFeatures, LayerSummary, MissionPage

MISSION_BASE_URL = "https://server.mapid.io/web/competition"
GEOSERVER_BASE_URL = "https://geoserver.mapid.io"


class MapidApiError(Exception):
    pass


class MapidClient(Protocol):
    async def fetch_missions(
        self,
        dataset: Dataset,
        polygon: Polygon,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        hashtag: list[str] | None = None,
        author: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MissionPage: ...

    async def fetch_layer(self, layer_id: str, project_id: str) -> LayerFeatures: ...

    async def fetch_layer_list(self, project_id: str) -> list[LayerSummary]: ...

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str: ...


def _extract_id(item: dict) -> str:
    if "_id" in item:
        return str(item["_id"])
    properties = item.get("properties", {})
    if "_id" in properties:
        return str(properties["_id"])
    raise MapidApiError("mission feature missing _id")


def _extract_layer_feature_id(item: dict, layer_id: str) -> str:
    """Stable id for a geoserver feature.

    Geoserver spells the per-feature id `id` (a uuid), not `_id` like the
    mission API. `fid` is the source shapefile's row number and is only unique
    within a layer, so it is namespaced by layer before being used as a
    fallback.
    """
    if "id" in item:
        return str(item["id"])
    fid = item.get("properties", {}).get("fid")
    if fid is not None:
        return f"{layer_id}:{fid}"
    raise MapidApiError("geoserver layer feature missing id")


def _normalize_layer_list(payload: list) -> list[LayerSummary]:
    return [
        LayerSummary(
            layer_id=str(item.get("_id", "")),
            name=str(item.get("name", "")),
            geometry_type=item.get("type"),
            fields=[str(f.get("name", "")) for f in item.get("fields") or []],
        )
        for item in payload
    ]


def _normalize_layer(payload: dict) -> LayerFeatures:
    if "features" not in payload:
        raise MapidApiError(payload.get("message", "MAPID geoserver layer request failed"))

    layer_id = str(payload.get("layer_id", ""))
    return LayerFeatures(
        layer_id=layer_id,
        layer_name=str(payload.get("layer_name", "")),
        features=[
            Feature(
                external_id=_extract_layer_feature_id(item, layer_id),
                properties=item.get("properties", {}),
                geometry=item.get("geometry", {}),
            )
            for item in payload["features"]
        ],
    )


def _normalize(dataset: Dataset, payload: dict) -> MissionPage:
    if not payload.get("success", False):
        raise MapidApiError(payload.get("message", "MAPID mission API request failed"))

    if dataset == "activities":
        raw_items = payload.get("data", {}).get("activities", [])
        features = [
            Feature(
                external_id=_extract_id(item), properties=item, geometry=item.get("geometry", {})
            )
            for item in raw_items
        ]
    else:
        raw_items = payload.get("features", [])
        features = [
            Feature(
                external_id=_extract_id(item),
                properties=item.get("properties", item),
                geometry=item.get("geometry", {}),
            )
            for item in raw_items
        ]

    has_more = payload.get("pagination", {}).get("hasMore", False)
    return MissionPage(features=features, has_more=has_more)


class HttpMapidClient:
    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient,
        geoserver_api_key: str = "",
    ) -> None:
        self._api_key = api_key
        # Two genuinely different credentials, verified: the mission key is a
        # 24-char ObjectId and the geoserver key a 32-char hex string, and each
        # is rejected by the other host (mission 500s, geoserver 404s). The
        # fallback only covers a deployment that has been given one of them.
        self._geoserver_api_key = geoserver_api_key or api_key
        self._http_client = http_client

    async def fetch_missions(
        self,
        dataset: Dataset,
        polygon: Polygon,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        hashtag: list[str] | None = None,
        author: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MissionPage:
        body = {"feature": mapping(polygon), "limit": limit, "offset": offset}
        if start_date is not None:
            body["start_date"] = start_date.isoformat()
        if end_date is not None:
            body["end_date"] = end_date.isoformat()
        if hashtag is not None:
            body["hashtag"] = hashtag
        if author is not None:
            body["author"] = author

        response = await self._http_client.post(
            f"{MISSION_BASE_URL}/{dataset}",
            json=body,
            headers={"x-api-key": self._api_key},
        )
        response.raise_for_status()
        return _normalize(dataset, response.json())

    async def fetch_layer(self, layer_id: str, project_id: str) -> LayerFeatures:
        response = await self._http_client.get(
            f"{GEOSERVER_BASE_URL}/layers_new/get_layer",
            params={
                "api_key": self._geoserver_api_key,
                "layer_id": layer_id,
                "project_id": project_id,
            },
        )
        response.raise_for_status()
        return _normalize_layer(response.json())

    async def fetch_layer_list(self, project_id: str) -> list[LayerSummary]:
        response = await self._http_client.get(
            f"{GEOSERVER_BASE_URL}/layers_new/get_layer_list",
            params={"api_key": self._geoserver_api_key, "project_id": project_id},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise MapidApiError("MAPID geoserver layer list request failed")
        return _normalize_layer_list(payload)

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return f"https://v2.basemap.mapid.io/styles/{style}/style.json?key={key}"


class FakeMapidClient:
    def __init__(
        self,
        fixtures: dict[Dataset, MissionPage],
        layers: dict[str, LayerFeatures] | None = None,
    ) -> None:
        self._fixtures = fixtures
        self._layers = layers or {}

    async def fetch_missions(
        self,
        dataset: Dataset,
        polygon: Polygon,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        hashtag: list[str] | None = None,
        author: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MissionPage:
        return self._fixtures.get(dataset, MissionPage(features=[], has_more=False))

    async def fetch_layer(self, layer_id: str, project_id: str) -> LayerFeatures:
        return self._layers.get(
            layer_id, LayerFeatures(layer_id=layer_id, layer_name="", features=[])
        )

    async def fetch_layer_list(self, project_id: str) -> list[LayerSummary]:
        return [
            LayerSummary(layer_id=layer.layer_id, name=layer.layer_name)
            for layer in self._layers.values()
        ]

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return HttpMapidClient.basemap_style_url(style, key)
