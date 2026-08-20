from pydantic import BaseModel


class StopRow(BaseModel):
    id: int
    lon: float
    lat: float


class RouteRow(BaseModel):
    id: int
    headway_min: float
    fare_idr: int


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
    walk_nodes: list[WalkNodeRow] = []
    walk_edges: list[WalkEdgeRow] = []
