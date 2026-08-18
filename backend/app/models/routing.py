from typing import Literal

from pydantic import BaseModel

Optimize = Literal["tercepat", "termurah", "termudah"]

EdgeType = Literal["walk", "board", "ride", "alight", "transfer", "andong", "becak"]


class RouteLeg(BaseModel):
    mode: EdgeType
    from_node: str
    to_node: str
    time_s: float
    fare_idr: int
    distance_m: float = 0.0


class Route(BaseModel):
    legs: list[RouteLeg]
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
