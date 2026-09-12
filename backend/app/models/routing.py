from typing import Literal

from pydantic import BaseModel, Field

Optimize = Literal["tercepat", "termurah", "termudah"]
TransitMode = Literal["walk", "bus", "rail", "airport_rail", "andong", "becak"]

EdgeType = Literal["walk", "board", "ride", "alight", "transfer", "andong", "becak"]


class RouteLeg(BaseModel):
    mode: EdgeType
    from_node: str
    to_node: str
    time_s: float
    fare_idr: int
    distance_m: float = 0.0
    from_name: str | None = None
    to_name: str | None = None
    transit_mode: TransitMode | None = None
    service_name: str | None = None
    operator: str | None = None
    source: str | None = None
    # The leg's polyline as [lon, lat] pairs, for drawing it on the map. Two
    # points today — node to node — since no shape geometry has been digitized
    # yet; a real shape drops in here without changing the contract. Empty when
    # either endpoint has no coordinate on the graph.
    coordinates: list[list[float]] = Field(default_factory=list)


class RouteStopSurvey(BaseModel):
    by: str | None = None
    community: str | None = None
    at: str | None = None


class RouteStopService(BaseModel):
    route_id: int
    name: str | None = None
    operator: str | None = None
    mode: str | None = None
    headway_min: float | None = None
    fare_idr: int | None = None
    source: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    freshness_status: str | None = None
    service_basis: str | None = None
    service_start_local: str | None = None
    service_end_local: str | None = None
    headway_min_minutes: float | None = None
    headway_max_minutes: float | None = None
    headway_is_approximate: bool | None = None
    next_departures: list[str] = Field(default_factory=list)


class StopDeparture(BaseModel):
    stop_id: str
    route_id: int
    service_name: str
    trip_external_id: str
    scheduled_time_local: str
    day_offset: int = 0
    is_estimated: bool = False
    source: str
    effective_from: str | None = None
    effective_until: str | None = None
    freshness_as_of: str | None = None
    freshness_status: str


class RouteStopDetail(BaseModel):
    id: str
    database_id: int
    external_id: str | None = None
    name: str | None = None
    coord: list[float]
    photo_url: str | None = None
    photos: list[str] = Field(default_factory=list)
    description: str | None = None
    survey: RouteStopSurvey | None = None
    routes: list[RouteStopService] = Field(default_factory=list)
    source: str | None = None
    effective_from: str | None = None
    freshness_status: str | None = None


class Route(BaseModel):
    legs: list[RouteLeg]
    stops: list[RouteStopDetail] = Field(default_factory=list)
    total_time_s: float
    total_fare_idr: int
    total_distance_m: float
    transfers: int


class Itinerary(BaseModel):
    stop_order: list[str]
    legs: list[Route]
    total_time_s: float
    total_fare_idr: int


class EmissionFactor(BaseModel):
    mode: str
    g_co2_per_km: float
    source_citation: str


class CarbonResult(BaseModel):
    saved_g_co2: float
    mode: str
    distance_km: float
    source_citation: str
