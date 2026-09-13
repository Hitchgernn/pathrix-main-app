"""One-off: parse the user's GraphHopper GPX export into demo_bus_polyline.json.

Run manually (`uv run python -m app.agent.build_demo_bus_polyline`) whenever
`routes/halte-rs-sardjito-halte-malioboro-1.gpx` is replaced with a new
export — not part of any import chain, just how `demo_route.py`'s fixture
polyline was produced.
"""

import json
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

GPX_PATH = Path(__file__).parents[3] / "routes" / "halte-rs-sardjito-halte-malioboro-1.gpx"
OUTPUT_PATH = Path(__file__).parent / "demo_bus_polyline.json"


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon_a, lat_a = map(radians, a)
    lon_b, lat_b = map(radians, b)
    value = sin((lat_b - lat_a) / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin((lon_b - lon_a) / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))


def main() -> None:
    text = GPX_PATH.read_text()
    points = re.findall(r'lat="(-?\d+\.\d+)" lon="(-?\d+\.\d+)"', text)
    coordinates = [[round(float(lon), 6), round(float(lat), 6)] for lat, lon in points]
    distance_m = sum(
        _haversine_m(a, b) for a, b in zip(coordinates, coordinates[1:], strict=False)
    )

    OUTPUT_PATH.write_text(
        json.dumps({"coordinates": coordinates, "distance_m": round(distance_m, 1)})
    )
    print(f"{len(coordinates)} points, {distance_m:.1f} m -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
