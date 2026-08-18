from datetime import date
from typing import Literal

from pydantic import BaseModel

Dataset = Literal["menugo", "propertigo", "struckgo", "activities"]


class Feature(BaseModel):
    external_id: str
    properties: dict
    geometry: dict


class MissionPage(BaseModel):
    features: list[Feature]
    has_more: bool


class MissionQuery(BaseModel):
    dataset: Dataset
    polygon_geojson: dict
    start_date: date | None = None
    end_date: date | None = None
    hashtag: list[str] | None = None
    author: str | None = None
    limit: int = 100
    offset: int = 0
