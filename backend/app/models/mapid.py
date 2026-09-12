from datetime import date
from typing import Literal

from pydantic import BaseModel

Dataset = Literal["menugo", "propertigo", "struckgo", "activities"]


class Feature(BaseModel):
    external_id: str
    properties: dict
    geometry: dict


class LayerFeatures(BaseModel):
    """One MAPID geoserver vector layer, fetched whole.

    The geoserver endpoint has no pagination: `get_layer` returns the entire
    FeatureCollection in one response, unlike the mission API's offset pages.
    """

    layer_id: str
    layer_name: str
    features: list[Feature]


class LayerSummary(BaseModel):
    """One row of a project's layer catalogue (`get_layer_list`)."""

    layer_id: str
    name: str
    geometry_type: str | None = None
    fields: list[str] = []


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
