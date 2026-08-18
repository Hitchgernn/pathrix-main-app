from typing import Literal

from pydantic import BaseModel

ComponentStatus = Literal["ok", "degraded", "down"]


class HealthStatus(BaseModel):
    db: ComponentStatus
    redis: ComponentStatus
    graph_loaded: bool
