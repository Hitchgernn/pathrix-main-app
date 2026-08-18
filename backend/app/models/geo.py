from pydantic import BaseModel


class Coord(BaseModel):
    lat: float
    lon: float


class BBox(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
