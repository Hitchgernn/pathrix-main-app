from datetime import date
from typing import Protocol

import httpx
from shapely import Polygon
from shapely.geometry import mapping

from app.models.mapid import Dataset, Feature, MissionPage

MISSION_BASE_URL = "https://server.mapid.io/web/competition"


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

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str: ...


def _extract_id(item: dict) -> str:
    if "_id" in item:
        return str(item["_id"])
    properties = item.get("properties", {})
    if "_id" in properties:
        return str(properties["_id"])
    raise MapidApiError("mission feature missing _id")


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
    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
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

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return f"https://v2.basemap.mapid.io/styles/{style}/style.json?key={key}"


class FakeMapidClient:
    def __init__(self, fixtures: dict[Dataset, MissionPage]) -> None:
        self._fixtures = fixtures

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

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return HttpMapidClient.basemap_style_url(style, key)
