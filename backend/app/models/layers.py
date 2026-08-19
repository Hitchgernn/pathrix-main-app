from pydantic import BaseModel


class LayerMeta(BaseModel):
    id: str
    name: str
    queryable: bool
    description: str


class IsochroneOut(BaseModel):
    stop_id: int
    minutes: int
    geometry: dict
