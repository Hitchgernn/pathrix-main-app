from collections.abc import Callable

from app.routing.constants import W_TRANSFER, W_WALK

BASE_WEIGHTS: dict[str, Callable[[dict], float]] = {
    "tercepat": lambda e: e["time_s"],
    "termurah": lambda e: e["fare_idr"],
    "termudah": lambda e: e["transfers"] * W_TRANSFER + e["walk_m"] * W_WALK,
}


def multigraph_weight(optimize: str) -> Callable[[str, str, dict], float]:
    base = BASE_WEIGHTS[optimize]

    def weight(u: str, v: str, parallel_edges: dict) -> float:
        return min(base(attrs) for attrs in parallel_edges.values())

    return weight
