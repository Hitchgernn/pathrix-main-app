"""Road-following geometry for adjacent, Activity-backed bus stops.

The normalized schedule importer intentionally keeps an all-or-nothing route
graph. This module has a narrower contract: retain every adjacent pair whose
two endpoint Activities resolve, even when other stops still block the route.
OSM supplies an estimated driving path for display only; timetable travel time
continues to own routing weights.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from geoalchemy2 import WKTElement
from shapely.geometry import LineString
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.schema import TransitRouteSegmentGeometry
from app.data.transport_pilot import PilotValidationError, _combined_reviews, _read_csv

ROAD_GEOMETRY_SOURCE = "osm_drive_estimated"
MAX_SNAP_DISTANCE_M = 250.0
_BBOX_PADDING_DEG = 0.01


@dataclass(frozen=True)
class ApprovedSegment:
    route_id: str
    from_stop_sequence: int
    to_stop_sequence: int
    from_activity_id: str
    to_activity_id: str
    from_coordinate: tuple[float, float]
    to_coordinate: tuple[float, float]


@dataclass(frozen=True)
class RoadSegmentGeometry:
    segment: ApprovedSegment
    coordinates: tuple[tuple[float, float], ...]
    distance_m: float


def build_approved_segment_plan(
    snapshot_dir: Path, *, review_paths: tuple[Path, ...] = ()
) -> tuple[ApprovedSegment, ...]:
    """Return only source-adjacent pairs with real Activity endpoints.

    Reuses schedule-match rules exactly: an exact normalized match wins; an
    approved review is accepted only when its candidate exists in the Activity
    catalogue. Missing or rejected positions create a gap, never a bridge.
    """
    stops = {row["stop_id"]: row for row in _read_csv(snapshot_dir / "stops.csv")}
    activities = {
        row["source_id"]: row for row in _read_csv(snapshot_dir / "activity_stop_catalog.csv")
    }
    reviews = _combined_reviews(review_paths)

    def resolve(route_id: str, source_stop_id: str) -> str | None:
        stop = stops.get(source_stop_id)
        if stop is None:
            return None
        exact = stop.get("matched_activity_id")
        if stop.get("match_status") == "matched_exact" and exact in activities:
            return exact
        reviewed = reviews.get((route_id, source_stop_id))
        if reviewed and reviewed["candidate_activity_id"] in activities:
            return reviewed["candidate_activity_id"]
        return None

    path_rows = _read_csv(snapshot_dir / "route_stops.csv")
    by_route: dict[str, list[dict[str, str]]] = {}
    for row in path_rows:
        by_route.setdefault(row["route_id"], []).append(row)

    segments: list[ApprovedSegment] = []
    for route_id, rows in by_route.items():
        ordered = sorted(rows, key=lambda row: int(row["stop_sequence"]))
        for previous, current in zip(ordered, ordered[1:], strict=False):
            from_sequence = int(previous["stop_sequence"])
            to_sequence = int(current["stop_sequence"])
            if to_sequence != from_sequence + 1:
                continue
            from_activity_id = resolve(route_id, previous["stop_id"])
            to_activity_id = resolve(route_id, current["stop_id"])
            if not from_activity_id or not to_activity_id:
                continue
            start, end = activities[from_activity_id], activities[to_activity_id]
            segments.append(
                ApprovedSegment(
                    route_id=route_id,
                    from_stop_sequence=from_sequence,
                    to_stop_sequence=to_sequence,
                    from_activity_id=from_activity_id,
                    to_activity_id=to_activity_id,
                    from_coordinate=(float(start["longitude"]), float(start["latitude"])),
                    to_coordinate=(float(end["longitude"]), float(end["latitude"])),
                )
            )
    return tuple(segments)


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt

    lon_a, lat_a = map(radians, a)
    lon_b, lat_b = map(radians, b)
    value = sin((lat_b - lat_a) / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin((lon_b - lon_a) / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))


def _edge_coordinates(graph, start, end) -> list[tuple[float, float]]:
    edges = graph.get_edge_data(start, end)
    if not edges:
        raise PilotValidationError(f"OSM path edge missing: {start!r} -> {end!r}")
    data = min(edges.values(), key=lambda value: value.get("length", float("inf")))
    geometry = data.get("geometry")
    coordinates = (
        list(geometry.coords)
        if geometry is not None
        else [
            (graph.nodes[start]["x"], graph.nodes[start]["y"]),
            (graph.nodes[end]["x"], graph.nodes[end]["y"]),
        ]
    )
    start_coordinate = (graph.nodes[start]["x"], graph.nodes[start]["y"])
    if _haversine_m(coordinates[0], start_coordinate) > _haversine_m(
        coordinates[-1], start_coordinate
    ):
        coordinates.reverse()
    return [(float(lon), float(lat)) for lon, lat in coordinates]


def _drive_graph(segments: tuple[ApprovedSegment, ...]):
    import osmnx as ox

    points = [
        coordinate
        for segment in segments
        for coordinate in (segment.from_coordinate, segment.to_coordinate)
    ]
    if not points:
        return None
    lons, lats = zip(*points, strict=True)
    bbox = (
        min(lons) - _BBOX_PADDING_DEG,
        min(lats) - _BBOX_PADDING_DEG,
        max(lons) + _BBOX_PADDING_DEG,
        max(lats) + _BBOX_PADDING_DEG,
    )
    return ox.graph_from_bbox(bbox, network_type="drive", retain_all=True, truncate_by_edge=True)


def _route_segment(graph, segment: ApprovedSegment) -> RoadSegmentGeometry | None:
    start_node, start_snap = ox_nearest_node(graph, segment.from_coordinate)
    end_node, end_snap = ox_nearest_node(graph, segment.to_coordinate)
    if max(start_snap, end_snap) > MAX_SNAP_DISTANCE_M:
        return None
    try:
        path = nx.shortest_path(graph, start_node, end_node, weight="length")
    except nx.NetworkXNoPath:
        return None
    coordinates: list[tuple[float, float]] = [segment.from_coordinate]
    for first, second in zip(path, path[1:], strict=False):
        edge = _edge_coordinates(graph, first, second)
        coordinates.extend(edge if coordinates[-1] != edge[0] else edge[1:])
    if coordinates[-1] != segment.to_coordinate:
        coordinates.append(segment.to_coordinate)
    if len(coordinates) < 2:
        return None
    return RoadSegmentGeometry(
        segment=segment,
        coordinates=tuple(coordinates),
        distance_m=sum(
            _haversine_m(first, second)
            for first, second in zip(coordinates, coordinates[1:], strict=False)
        ),
    )


def ox_nearest_node(graph, coordinate: tuple[float, float]) -> tuple[object, float]:
    """Nearest drive node without OSMnx's optional scikit-learn extra.

    The one city graph is reused for every segment, and this fallback keeps the
    ingest runnable in the project's minimal ``osmnx`` installation. It also
    gives us a stable seam for unit tests.
    """
    candidates = graph.graph.setdefault(
        "_pathrix_node_coordinates",
        [(node, float(data["x"]), float(data["y"])) for node, data in graph.nodes(data=True)],
    )
    lon, lat = coordinate
    node, node_lon, node_lat = min(
        candidates, key=lambda candidate: (candidate[1] - lon) ** 2 + (candidate[2] - lat) ** 2
    )
    return node, _haversine_m(coordinate, (node_lon, node_lat))


async def route_approved_segments(
    segments: tuple[ApprovedSegment, ...],
) -> tuple[RoadSegmentGeometry, ...]:
    graph = await asyncio.to_thread(_drive_graph, segments)
    if graph is None:
        return ()
    routed = await asyncio.to_thread(
        lambda: [_route_segment(graph, segment) for segment in segments]
    )
    return tuple(result for result in routed if result is not None)


async def upsert_road_segment_geometries(
    session: AsyncSession, segments: tuple[RoadSegmentGeometry, ...]
) -> int:
    """Idempotently retain generated geometry; no transit route rows are touched."""
    if not segments:
        return 0
    values = [
        {
            "route_id": road.segment.route_id,
            "from_stop_sequence": road.segment.from_stop_sequence,
            "to_stop_sequence": road.segment.to_stop_sequence,
            "from_activity_id": road.segment.from_activity_id,
            "to_activity_id": road.segment.to_activity_id,
            "geom": WKTElement(LineString(road.coordinates).wkt, srid=4326),
            "distance_m": road.distance_m,
            "source": ROAD_GEOMETRY_SOURCE,
        }
        for road in segments
    ]
    stmt = pg_insert(TransitRouteSegmentGeometry).values(values)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[
                TransitRouteSegmentGeometry.route_id,
                TransitRouteSegmentGeometry.from_stop_sequence,
                TransitRouteSegmentGeometry.to_stop_sequence,
            ],
            set_={
                "from_activity_id": stmt.excluded.from_activity_id,
                "to_activity_id": stmt.excluded.to_activity_id,
                "geom": stmt.excluded.geom,
                "distance_m": stmt.excluded.distance_m,
                "source": stmt.excluded.source,
                "updated_at": func.now(),
            },
        )
    )
    return len(segments)


def write_road_segment_geojson(path: Path, segments: tuple[RoadSegmentGeometry, ...]) -> None:
    """Persist a portable artifact before an optional database import."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "route_id": road.segment.route_id,
                    "from_stop_sequence": road.segment.from_stop_sequence,
                    "to_stop_sequence": road.segment.to_stop_sequence,
                    "from_activity_id": road.segment.from_activity_id,
                    "to_activity_id": road.segment.to_activity_id,
                    "distance_m": road.distance_m,
                    "source": ROAD_GEOMETRY_SOURCE,
                    "estimated": True,
                },
                "geometry": {"type": "LineString", "coordinates": road.coordinates},
            }
            for road in segments
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


async def road_segment_report(session: AsyncSession) -> dict[str, int]:
    total = await session.scalar(select(func.count()).select_from(TransitRouteSegmentGeometry))
    return {"stored_segments": int(total or 0)}
