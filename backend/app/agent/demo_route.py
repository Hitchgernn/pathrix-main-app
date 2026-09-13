"""Hand-authored Route fixture for demo recordings, standing in for calculate_route.

Real bus topology (`route_stops`) is empty across the whole dataset right now
(the schedule-import review effort found ~80 stop positions still unresolved
across routes 12/3A/3B/4A/4B, and the same gate applies to every other route),
so `calculate_route` can only ever return a walk-only path today. This fixture
is not a random invention.

Halte RS Sardjito Timur is itself a real stop on route 3A (sequence 6, right
before FKG UGM/GIK UGM) — user-confirmed and approved this session
(`route3a_shared_remaining_manual_review.v1.csv`, copying an already-approved
match from route 4B). So the walker boards there directly rather than walking
past it to Kopma UGM: the walk leg is a short, real local-walk-network path
from Fakultas Teknik UGM to Halte RS Sardjito Timur (303.0m, 227.8s), and the
ride leg starts at Sardjito Timur itself.

Swapped in for `make_calculate_route_tool` only when `settings.demo_mock_route`
is set (`AgentRuntime.create`) — the real LLM still plans/narrates/calls tools
normally; only this one tool's data is pre-authored.

The bus leg's polyline (`demo_bus_polyline.json`) is a real, road-snapped
driving route from Halte RS Sardjito Timur straight to Halte Malioboro 1
(4119.9m, 125 points), computed by GraphHopper Maps (a proper drive-network
routing engine — solves the wrong-side-of-a-roundabout and one-way-street
artifacts a pedestrian-network proxy kept producing) and exported by the user
as GPX to `routes/halte-rs-sardjito-halte-malioboro-1.gpx`. Parsed into this
JSON by `app/agent/build_demo_bus_polyline.py` — re-run that (`uv run python
-m app.agent.build_demo_bus_polyline`) if the source GPX changes. Route 3A's
own "TPB Panti Rapih" waypoint between
these two stops is deliberately not named/stopped-at here on the user's
explicit call — it's actually a genuine, photographed community survey post
(shelter/ramp/guiding-block condition, dated 2026-08-22) whose pin sits ~96m
from the real hospital per a Nominatim geocode, so the underlying survey data
is likely fine; the actual confirmed-bad match this session found was a
*different* stop (`bus-rs-panti-nugroho-...`, fuzzy-matched to a
same-named-sounding but physically different hospital in Pakem, left
rejected as before).

The walk leg after alighting (`demo_walk_to_andong_polyline.json`) covers a
real andong stand near Halte Malioboro 1, ending exactly where the closing
andong leg's own GPX begins (19.6m from where the bus leg's polyline ends) so
all three legs meet without a visible jump. Distance/time are haversine +
`WALK_SPEED_MPS` (`routing/constants.py`), the same formula `walk_edge_attrs`
uses for a real walk edge — not invented.

The closing andong leg (`demo_andong_polyline.json`) is the actual last-mile
point the demo script asks about: a ride from that stand to Titik Nol
Kilometer Yogyakarta, down Jl. Malioboro/Jl. A. Yani. Same provenance as the
bus leg — a GraphHopper Maps road-network route, exported by the user as GPX
to `routes/andong-titik-nol.gpx` (5 points, 1165.3m) and parsed into this
JSON by `app/agent/build_demo_andong_polyline.py` (re-run that, `uv run
python -m app.agent.build_demo_andong_polyline`, if the source GPX changes).
`fare_base`/`fare_per_km` are null on every andong `pangkalan` row today (the
activity-survey harvest carries no fare field), so this leg's time/fare use
the same `andong_edge_attrs` formula (`routing/edges.py`) real routing would,
fed the flat rate `tests/routing` already uses for an andong edge
(`fare_base=5000, fare_per_km=2000, speed_mps=ANDONG_SPEED_MPS`) rather than
inventing a separate one here.
"""

import json
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from app.models.geo import Coord
from app.models.routing import Optimize, Route, RouteLeg, TransitMode
from app.routing.build import ANDONG_SPEED_MPS
from app.routing.edges import andong_edge_attrs

_WALK_POLYLINE = json.loads((Path(__file__).parent / "demo_walk_polyline.json").read_text())
_BUS_POLYLINE = json.loads((Path(__file__).parent / "demo_bus_polyline.json").read_text())
_WALK_TO_ANDONG_POLYLINE = json.loads(
    (Path(__file__).parent / "demo_walk_to_andong_polyline.json").read_text()
)
_ANDONG_POLYLINE = json.loads((Path(__file__).parent / "demo_andong_polyline.json").read_text())

_WALK_COORDINATES = _WALK_POLYLINE["coordinates"]
_WALK_DISTANCE_M = _WALK_POLYLINE["distance_m"]
_WALK_TIME_S = _WALK_POLYLINE["time_s"]

_BUS_COORDINATES = _BUS_POLYLINE["coordinates"]
_BUS_DISTANCE_M = _BUS_POLYLINE["distance_m"]

_WALK_TO_ANDONG_COORDINATES = _WALK_TO_ANDONG_POLYLINE["coordinates"]
_WALK_TO_ANDONG_DISTANCE_M = _WALK_TO_ANDONG_POLYLINE["distance_m"]
_WALK_TO_ANDONG_TIME_S = _WALK_TO_ANDONG_POLYLINE["time_s"]

_ANDONG_COORDINATES = _ANDONG_POLYLINE["coordinates"]
_ANDONG_DISTANCE_M = _ANDONG_POLYLINE["distance_m"]
_ANDONG_ATTRS = andong_edge_attrs(
    _ANDONG_DISTANCE_M, ANDONG_SPEED_MPS, fare_base=5000, fare_per_km=2000
)
_ANDONG_TIME_S = _ANDONG_ATTRS["time_s"]
_ANDONG_FARE_IDR = _ANDONG_ATTRS["fare_idr"]

# A real drive-network shortest path isn't a straight shot between stops —
# Yogyakarta's one-way grid makes this genuinely longer than the straight-line
# distance. A priority-lane bus average (25 km/h) keeps the duration honest to
# that real distance rather than reusing a generic-car estimate.
_BUS_TIME_S = round(_BUS_DISTANCE_M / (25_000 / 3600), 1)
_BOARD_TIME_S = 420.0
_ALIGHT_TIME_S = 30.0
_FARE_IDR = 3500

DEMO_ROUTE = Route(
    legs=[
        RouteLeg(
            mode="walk",
            from_node="poi:fakultas-teknik-ugm",
            to_node="stop:234",
            time_s=_WALK_TIME_S,
            fare_idr=0,
            distance_m=_WALK_DISTANCE_M,
            from_name="Fakultas Teknik UGM",
            to_name="Halte RS Sardjito Timur",
            transit_mode="walk",
            coordinates=_WALK_COORDINATES,
        ),
        RouteLeg(
            mode="board",
            from_node="stop:234",
            to_node="stop:234",
            time_s=_BOARD_TIME_S,
            fare_idr=_FARE_IDR,
            distance_m=0.0,
            from_name="Halte RS Sardjito Timur",
            to_name="Halte RS Sardjito Timur",
            transit_mode="bus",
            service_name="3A",
            operator="TransJogja",
        ),
        RouteLeg(
            mode="ride",
            from_node="stop:234",
            to_node="stop:malioboro-1",
            time_s=_BUS_TIME_S,
            fare_idr=0,
            distance_m=_BUS_DISTANCE_M,
            from_name="Halte RS Sardjito Timur",
            to_name="Halte Malioboro 1",
            transit_mode="bus",
            service_name="3A",
            operator="TransJogja",
            coordinates=_BUS_COORDINATES,
        ),
        RouteLeg(
            mode="alight",
            from_node="stop:malioboro-1",
            to_node="stop:malioboro-1",
            time_s=_ALIGHT_TIME_S,
            fare_idr=0,
            distance_m=0.0,
            from_name="Halte Malioboro 1",
            to_name="Halte Malioboro 1",
            transit_mode="bus",
        ),
        RouteLeg(
            mode="walk",
            from_node="stop:malioboro-1",
            to_node="pangkalan:andong-malioboro",
            time_s=_WALK_TO_ANDONG_TIME_S,
            fare_idr=0,
            distance_m=_WALK_TO_ANDONG_DISTANCE_M,
            from_name="Halte Malioboro 1",
            to_name="Andong Malioboro",
            transit_mode="walk",
            coordinates=_WALK_TO_ANDONG_COORDINATES,
        ),
        RouteLeg(
            mode="andong",
            from_node="pangkalan:andong-malioboro",
            to_node="poi:titik-nol",
            time_s=_ANDONG_TIME_S,
            fare_idr=_ANDONG_FARE_IDR,
            distance_m=_ANDONG_DISTANCE_M,
            from_name="Andong Malioboro",
            to_name="Titik Nol Kilometer",
            transit_mode="andong",
            coordinates=_ANDONG_COORDINATES,
        ),
    ],
    total_time_s=_WALK_TIME_S
    + _BOARD_TIME_S
    + _BUS_TIME_S
    + _ALIGHT_TIME_S
    + _WALK_TO_ANDONG_TIME_S
    + _ANDONG_TIME_S,
    total_fare_idr=_FARE_IDR + _ANDONG_FARE_IDR,
    total_distance_m=_WALK_DISTANCE_M
    + _BUS_DISTANCE_M
    + _WALK_TO_ANDONG_DISTANCE_M
    + _ANDONG_DISTANCE_M,
    transfers=0,
)


def make_demo_calculate_route_tool() -> BaseTool:
    async def calculate_route(
        start: str | Coord, end: str | Coord, modes: list[TransitMode], optimize: Optimize
    ) -> Route:
        """Compute a multimodal route. Use public modes such as bus, rail, or walk."""
        return DEMO_ROUTE

    return tool(calculate_route)
