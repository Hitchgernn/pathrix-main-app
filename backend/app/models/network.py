from pydantic import BaseModel, Field


class StopServiceRow(BaseModel):
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


class StopRow(BaseModel):
    id: int
    lon: float
    lat: float
    name: str | None = None
    external_id: str | None = None
    photo_url: str | None = None
    photos: list[str] = Field(default_factory=list)
    description: str | None = None
    surveyor: str | None = None
    community: str | None = None
    surveyed_at: str | None = None
    source: str | None = None
    routes: list[StopServiceRow] = Field(default_factory=list)


class RouteRow(BaseModel):
    id: int
    headway_min: float
    fare_idr: int
    name: str | None = None
    operator: str | None = None
    mode: str | None = None
    source: str | None = None


class RouteStopRow(BaseModel):
    route_id: int
    stop_id: int
    seq: int
    travel_time_from_prev_s: int | None


class PangkalanRow(BaseModel):
    id: int
    type: str
    lon: float
    lat: float
    fare_base: int
    fare_per_km: float


class WalkNodeRow(BaseModel):
    id: int
    lon: float
    lat: float


class WalkEdgeRow(BaseModel):
    u: int
    v: int
    length_m: float


class NetworkData(BaseModel):
    stops: list[StopRow]
    routes: list[RouteRow]
    route_stops: list[RouteStopRow]
    pangkalan: list[PangkalanRow]
    walk_nodes: list[WalkNodeRow] = Field(default_factory=list)
    walk_edges: list[WalkEdgeRow] = Field(default_factory=list)
