import json
import re
from datetime import datetime
from typing import Literal

from sqlalchemy import String, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.schema import (
    EmissionFactor as EmissionFactorRow,
)
from app.data.schema import (
    Pangkalan,
    Poi,
    Properti,
    RouteStop,
    StopManualReview,
    TransitRoute,
    TransitRouteSegmentGeometry,
    TransitScheduleImport,
    TransitServiceProfile,
    TransitStop,
    TransitStopTime,
    TransitTrip,
    WalkEdge,
    WalkNode,
)
from app.models.geo import BBox
from app.models.mapid import Dataset, Feature
from app.models.network import (
    NetworkData,
    PangkalanRow,
    RouteRow,
    RouteSegmentGeometryRow,
    RouteStopRow,
    StopRow,
    StopServiceRow,
    WalkEdgeRow,
    WalkNodeRow,
)
from app.models.routing import EmissionFactor, StopDeparture
from app.models.search import PlaceHit

ViewportDataType = Literal["poi", "menugo", "struckgo", "properti", "transit", "pangkalan"]

_VIEWPORT_TABLES = {
    "poi": Poi,
    "menugo": Poi,
    "struckgo": Poi,
    "properti": Properti,
    "transit": TransitStop,
    "pangkalan": Pangkalan,
}


def _raw_text(raw: dict | None, *keys: str) -> str | None:
    for key in keys:
        value = (raw or {}).get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _raw_media(raw: dict | None) -> list[str]:
    medias = (raw or {}).get("medias")
    if not isinstance(medias, list):
        return []
    return [media for media in medias if isinstance(media, str) and media]


def _source_metadata(source: str | None) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for part in (source or "").split(";")[1:]:
        key, separator, value = part.partition("=")
        if separator and key and value:
            metadata[key] = value
    return metadata


def _not_filed_as_infrastructure() -> list:
    """Conditions excluding `poi` rows that a second pass filed elsewhere.

    `run_activity_survey_etl` copies a halte or a becak stand out of the
    `activities` feed into `transit_stops` / `pangkalan` and deliberately
    leaves the original `poi` row in place as the unedited record of the post.
    Without this the same shelter is two search results and two map markers at
    one coordinate — one of them under "Pariwisata & Sosial Budaya", which is
    not what it is.
    """
    return [
        ~select(TransitStop.id).where(TransitStop.external_id == Poi.external_id).exists(),
        ~select(Pangkalan.id).where(Pangkalan.external_id == Poi.external_id).exists(),
    ]


async def query_features_in_viewport(
    session: AsyncSession, data_type: ViewportDataType, bbox: BBox, limit: int = 50
) -> list[Feature]:
    table = _VIEWPORT_TABLES[data_type]
    envelope = func.ST_MakeEnvelope(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326)
    source_type = table.source if table is Poi else data_type
    stmt = (
        select(
            table.external_id,
            table.raw,
            source_type.label("source_type")
            if table is Poi
            else func.cast(source_type, String).label("source_type"),
            func.ST_AsGeoJSON(table.geom).label("geom_json"),
        )
        .where(func.ST_Intersects(table.geom, envelope))
        .limit(limit)
    )
    if data_type == "poi":
        stmt = stmt.where(Poi.source == "activities", *_not_filed_as_infrastructure())
    elif data_type in {"menugo", "struckgo"}:
        stmt = stmt.where(Poi.source == data_type)
    result = await session.execute(stmt)
    return [
        Feature(
            external_id=row.external_id,
            properties={**row.raw, "source_type": row.source_type},
            geometry=json.loads(row.geom_json),
        )
        for row in result
    ]


async def fetch_manually_reviewed_stop_external_ids(session: AsyncSession) -> list[str]:
    """external_ids of every stop with at least one StopManualReview row — used
    by the frontend to draw a real pin instead of the flat circle dot for a
    field-survey-reviewed location."""
    stmt = (
        select(TransitStop.external_id)
        .join(StopManualReview, StopManualReview.stop_id == TransitStop.id)
        .where(TransitStop.external_id.is_not(None))
        .distinct()
    )
    result = await session.execute(stmt)
    return [row[0] for row in result]


async def fetch_estimated_transit_segments(session: AsyncSession, bbox: BBox) -> dict[str, object]:
    """GeoJSON road estimates for reviewed adjacent stop pairs in a viewport."""
    envelope = func.ST_MakeEnvelope(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326)
    rows = await session.execute(
        select(
            TransitRouteSegmentGeometry.route_id,
            TransitRouteSegmentGeometry.from_stop_sequence,
            TransitRouteSegmentGeometry.to_stop_sequence,
            TransitRouteSegmentGeometry.from_activity_id,
            TransitRouteSegmentGeometry.to_activity_id,
            TransitRouteSegmentGeometry.distance_m,
            TransitRouteSegmentGeometry.source,
            func.ST_AsGeoJSON(TransitRouteSegmentGeometry.geom),
        ).where(func.ST_Intersects(TransitRouteSegmentGeometry.geom, envelope))
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "route_id": row[0],
                    "from_stop_sequence": row[1],
                    "to_stop_sequence": row[2],
                    "from_activity_id": row[3],
                    "to_activity_id": row[4],
                    "distance_m": row[5],
                    "source": row[6],
                    "estimated": True,
                },
                "geometry": json.loads(row[7]),
            }
            for row in rows
        ],
    }


async def search_places(session: AsyncSession, query: str, limit: int = 8) -> list[PlaceHit]:
    """Name search over every mirrored table that has a point and a label.

    Ordered transit stops first, then andong/becak stands, then mission rows:
    someone typing into a mobility app's search box is far more often looking
    for a halte than for a listing that happens to share the word. Matching is
    a case-insensitive substring (`ILIKE`), not full-text — the corpus is a few
    hundred rows per table, and a tsvector index would be machinery without a
    workload to justify it yet.
    """
    term = f"%{query.strip()}%"
    if not query.strip():
        return []

    hits: list[PlaceHit] = []

    stops = await session.execute(
        select(
            TransitStop.id,
            TransitStop.external_id,
            TransitStop.name,
            TransitStop.operator,
            func.ST_X(TransitStop.geom),
            func.ST_Y(TransitStop.geom),
            TransitStop.raw,
        )
        .where(TransitStop.name.ilike(term))
        .limit(limit)
    )
    for stop_id, external_id, name, operator, lon, lat, raw in stops:
        hits.append(
            PlaceHit(
                # The stop-departures lookup keys on the MAPID Activity id, not
                # our internal row id — fall back only for a stop ingested
                # without one (the geoserver halte layer predates external_id).
                id=f"transit:{external_id or stop_id}",
                name=name,
                kind="transit",
                subtitle=operator,
                lon=lon,
                lat=lat,
                raw=raw,
            )
        )

    stands = await session.execute(
        select(
            Pangkalan.id,
            Pangkalan.name,
            Pangkalan.type,
            func.ST_X(Pangkalan.geom),
            func.ST_Y(Pangkalan.geom),
            Pangkalan.raw,
        )
        .where(Pangkalan.name.ilike(term))
        .limit(limit)
    )
    for stand_id, name, kind, lon, lat, raw in stands:
        hits.append(
            PlaceHit(
                id=f"pangkalan:{stand_id}",
                name=name or f"Pangkalan {kind}",
                kind="pangkalan",
                subtitle=kind,
                lon=lon,
                lat=lat,
                raw=raw,
            )
        )

    pois = await session.execute(
        select(
            Poi.external_id,
            Poi.nama_tempat,
            Poi.kategori,
            func.ST_X(Poi.geom),
            func.ST_Y(Poi.geom),
            Poi.raw,
        )
        .where(Poi.nama_tempat.ilike(term), *_not_filed_as_infrastructure())
        .limit(limit)
    )
    for external_id, name, kategori, lon, lat, raw in pois:
        hits.append(
            PlaceHit(
                id=f"poi:{external_id}",
                name=name or "Tempat",
                kind="poi",
                subtitle=kategori,
                lon=lon,
                lat=lat,
                raw=raw,
            )
        )

    properti = await session.execute(
        select(
            Properti.external_id,
            Properti.alamat,
            Properti.jenis_properti,
            func.ST_X(Properti.geom),
            func.ST_Y(Properti.geom),
            Properti.raw,
        )
        .where(Properti.alamat.ilike(term))
        .limit(limit)
    )
    for external_id, alamat, jenis, lon, lat, raw in properti:
        hits.append(
            PlaceHit(
                id=f"properti:{external_id}",
                name=alamat or "Properti",
                kind="properti",
                subtitle=jenis,
                lon=lon,
                lat=lat,
                raw=raw,
            )
        )

    return hits[:limit]


async def fetch_network_data(session: AsyncSession) -> NetworkData:
    stop_rows = await session.execute(
        select(
            TransitStop.id,
            func.ST_X(TransitStop.geom),
            func.ST_Y(TransitStop.geom),
            TransitStop.name,
            TransitStop.external_id,
            TransitStop.raw,
            TransitStop.source,
        )
    )
    route_rows = await session.execute(
        select(
            TransitRoute.id,
            TransitRoute.headway_min,
            TransitRoute.fare_idr,
            TransitRoute.name,
            TransitRoute.operator,
            TransitRoute.mode,
            TransitRoute.source,
        )
    )
    route_stop_rows = await session.execute(
        select(
            RouteStop.route_id, RouteStop.stop_id, RouteStop.seq, RouteStop.travel_time_from_prev_s
        )
    )
    segment_geometry_rows = await session.execute(
        select(
            TransitRouteSegmentGeometry.route_id,
            TransitRouteSegmentGeometry.from_stop_sequence,
            TransitRouteSegmentGeometry.to_stop_sequence,
            func.ST_AsGeoJSON(TransitRouteSegmentGeometry.geom),
            TransitRouteSegmentGeometry.distance_m,
        )
    )
    profile_rows = await session.execute(
        select(
            TransitServiceProfile.route_id,
            TransitServiceProfile.basis,
            TransitServiceProfile.service_start_local,
            TransitServiceProfile.service_end_local,
            TransitServiceProfile.headway_min_minutes,
            TransitServiceProfile.headway_max_minutes,
            TransitServiceProfile.headway_is_approximate,
            TransitScheduleImport.effective_from,
            TransitScheduleImport.effective_until,
            TransitScheduleImport.freshness_status,
        )
        .join(
            TransitScheduleImport,
            TransitScheduleImport.id == TransitServiceProfile.schedule_import_id,
        )
        .where(TransitScheduleImport.status == "complete")
        .order_by(TransitScheduleImport.imported_at.desc())
    )
    pangkalan_rows = await session.execute(
        select(
            Pangkalan.id,
            Pangkalan.type,
            func.ST_X(Pangkalan.geom),
            func.ST_Y(Pangkalan.geom),
            Pangkalan.fare_base,
            Pangkalan.fare_per_km,
        ).where(Pangkalan.fare_base.is_not(None), Pangkalan.fare_per_km.is_not(None))
    )
    walk_node_rows = await session.execute(
        select(WalkNode.id, func.ST_X(WalkNode.geom), func.ST_Y(WalkNode.geom))
    )
    walk_edge_rows = await session.execute(select(WalkEdge.u, WalkEdge.v, WalkEdge.length_m))

    routes = [
        RouteRow(
            id=r[0],
            headway_min=r[1],
            fare_idr=r[2],
            name=r[3],
            operator=r[4],
            mode=r[5],
            source=r[6],
            source_route_id=(
                r[6].split(";", 1)[0].removeprefix("normalized-transport:")
                if r[6] and r[6].startswith("normalized-transport:")
                else None
            ),
        )
        for r in route_rows
    ]
    route_stops = [
        RouteStopRow(route_id=r[0], stop_id=r[1], seq=r[2], travel_time_from_prev_s=r[3])
        for r in route_stop_rows
    ]
    latest_profile_by_route = {}
    for profile in profile_rows:
        latest_profile_by_route.setdefault(profile[0], profile)
    routes_by_id = {route.id: route for route in routes}
    services_by_stop: dict[int, list[StopServiceRow]] = {}
    seen_stop_routes: set[tuple[int, int]] = set()
    for route_stop in route_stops:
        key = (route_stop.stop_id, route_stop.route_id)
        route = routes_by_id.get(route_stop.route_id)
        if route is None or key in seen_stop_routes:
            continue
        seen_stop_routes.add(key)
        source_meta = _source_metadata(route.source)
        profile = latest_profile_by_route.get(route.id)
        services_by_stop.setdefault(route_stop.stop_id, []).append(
            StopServiceRow(
                route_id=route.id,
                name=route.name,
                operator=route.operator,
                mode=route.mode,
                headway_min=route.headway_min,
                fare_idr=route.fare_idr,
                source=route.source,
                effective_from=(
                    profile[7].isoformat()
                    if profile is not None and profile[7] is not None
                    else source_meta.get("effective_from")
                ),
                effective_until=(
                    profile[8].isoformat()
                    if profile is not None and profile[8] is not None
                    else source_meta.get("effective_until")
                ),
                freshness_status=(
                    profile[9] if profile is not None else source_meta.get("freshness_status")
                ),
                service_basis=profile[1] if profile is not None else None,
                service_start_local=profile[2] if profile is not None else None,
                service_end_local=profile[3] if profile is not None else None,
                headway_min_minutes=profile[4] if profile is not None else None,
                headway_max_minutes=profile[5] if profile is not None else None,
                headway_is_approximate=profile[6] if profile is not None else None,
            )
        )

    stops = []
    for row in stop_rows:
        raw = row[5] or {}
        photos = _raw_media(raw)
        photo_url = _raw_text(raw, "foto_url", "photo_url") or (photos[0] if photos else None)
        stops.append(
            StopRow(
                id=row[0],
                lon=row[1],
                lat=row[2],
                name=row[3],
                external_id=row[4],
                photo_url=photo_url,
                photos=photos,
                description=_raw_text(raw, "description", "deskripsi"),
                surveyor=_raw_text(raw, "user_full_name", "user_name", "surveyor"),
                community=_raw_text(raw, "community_name"),
                surveyed_at=_raw_text(raw, "created_at", "surveyed_at", "tanggal"),
                source=row[6],
                routes=services_by_stop.get(row[0], []),
            )
        )

    return NetworkData(
        stops=stops,
        routes=routes,
        route_stops=route_stops,
        route_segment_geometries=[
            RouteSegmentGeometryRow(
                route_id=r[0],
                from_stop_sequence=r[1],
                to_stop_sequence=r[2],
                coordinates=json.loads(r[3])["coordinates"],
                distance_m=r[4],
            )
            for r in segment_geometry_rows
        ],
        pangkalan=[
            PangkalanRow(id=r[0], type=r[1], lon=r[2], lat=r[3], fare_base=r[4], fare_per_km=r[5])
            for r in pangkalan_rows
        ],
        walk_nodes=[WalkNodeRow(id=r[0], lon=r[1], lat=r[2]) for r in walk_node_rows],
        walk_edges=[WalkEdgeRow(u=r[0], v=r[1], length_m=r[2]) for r in walk_edge_rows],
    )


async def fetch_stop_departures(
    session: AsyncSession,
    external_stop_id: str,
    *,
    after_local: str | None = None,
    limit: int = 8,
) -> list[StopDeparture]:
    """Read imported timetable rows; never synthesizes departures from headway."""
    if (
        after_local is not None
        and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", after_local) is None
    ):
        raise ValueError("after_local must be a valid HH:MM or HH:MM:SS local time")
    statement = (
        select(
            TransitStop.external_id,
            TransitRoute.id,
            TransitRoute.name,
            TransitTrip.external_id,
            TransitStopTime.scheduled_time_local,
            TransitStopTime.day_offset,
            TransitStopTime.is_estimated,
            TransitScheduleImport.source_path,
            TransitScheduleImport.effective_from,
            TransitScheduleImport.effective_until,
            TransitScheduleImport.freshness_as_of,
            TransitScheduleImport.freshness_status,
        )
        .join(TransitTrip, TransitTrip.id == TransitStopTime.trip_id)
        .join(TransitRoute, TransitRoute.id == TransitTrip.route_id)
        .join(TransitStop, TransitStop.id == TransitStopTime.stop_id)
        .join(
            TransitScheduleImport,
            TransitScheduleImport.id == TransitTrip.schedule_import_id,
        )
        .where(
            TransitStop.external_id == external_stop_id,
            TransitScheduleImport.status == "complete",
        )
        .order_by(
            TransitStopTime.day_offset,
            TransitStopTime.scheduled_time_local,
        )
        .limit(limit)
    )
    if after_local is not None:
        statement = statement.where(
            or_(
                TransitStopTime.day_offset > 0,
                TransitStopTime.scheduled_time_local >= after_local,
            )
        )

    rows = await session.execute(statement)
    return [
        StopDeparture(
            stop_id=row[0],
            route_id=row[1],
            service_name=row[2],
            trip_external_id=row[3],
            scheduled_time_local=row[4],
            day_offset=row[5],
            is_estimated=row[6],
            source=row[7],
            effective_from=row[8].isoformat() if row[8] else None,
            effective_until=row[9].isoformat() if row[9] else None,
            freshness_as_of=row[10].isoformat() if row[10] else None,
            freshness_status=row[11],
        )
        for row in rows
    ]


# A real OSMnx pedestrian network for anything bigger than a neighbourhood
# easily produces tens of thousands of rows; asyncpg refuses a single bound
# statement past 32767 parameters, so a whole-list `.values([...])` blows up
# on any reasonably dense area. Chunk conservatively — well under the limit
# even at a few bound params per row.
_WALK_NETWORK_CHUNK_SIZE = 5000


async def upsert_walk_network(
    session: AsyncSession, nodes: list[WalkNodeRow], edges: list[WalkEdgeRow]
) -> tuple[int, int]:
    for start in range(0, len(nodes), _WALK_NETWORK_CHUNK_SIZE):
        chunk = nodes[start : start + _WALK_NETWORK_CHUNK_SIZE]
        node_stmt = pg_insert(WalkNode).values(
            [
                {"id": n.id, "geom": func.ST_SetSRID(func.ST_MakePoint(n.lon, n.lat), 4326)}
                for n in chunk
            ]
        )
        node_stmt = node_stmt.on_conflict_do_update(
            index_elements=[WalkNode.id], set_={"geom": node_stmt.excluded.geom}
        )
        await session.execute(node_stmt)

    for start in range(0, len(edges), _WALK_NETWORK_CHUNK_SIZE):
        chunk = edges[start : start + _WALK_NETWORK_CHUNK_SIZE]
        edge_stmt = pg_insert(WalkEdge).values(
            [{"u": e.u, "v": e.v, "length_m": e.length_m} for e in chunk]
        )
        edge_stmt = edge_stmt.on_conflict_do_update(
            index_elements=[WalkEdge.u, WalkEdge.v], set_={"length_m": edge_stmt.excluded.length_m}
        )
        await session.execute(edge_stmt)

    await session.commit()
    return len(nodes), len(edges)


async def fetch_emission_factors(session: AsyncSession) -> dict[str, EmissionFactor]:
    result = await session.execute(
        select(
            EmissionFactorRow.mode,
            EmissionFactorRow.g_co2_per_km,
            EmissionFactorRow.source_citation,
        )
    )
    return {
        row.mode: EmissionFactor(
            mode=row.mode, g_co2_per_km=row.g_co2_per_km, source_citation=row.source_citation
        )
        for row in result
    }


# Estimates, not a measured local study. Fuel-combustion modes (private_vehicle,
# bus) cite KLHK 2023's national fuel emission factors; grid-electric and
# non-motorized modes (rail, airport_rail, andong, becak, walk) cite IPCC 2006
# Tier 1 default methodology.
DEFAULT_EMISSION_FACTORS: list[EmissionFactor] = [
    EmissionFactor(mode="private_vehicle", g_co2_per_km=192.0, source_citation="KLHK 2023"),
    EmissionFactor(mode="bus", g_co2_per_km=95.0, source_citation="KLHK 2023"),
    EmissionFactor(mode="rail", g_co2_per_km=41.0, source_citation="IPCC 2006 Tier 1"),
    EmissionFactor(mode="airport_rail", g_co2_per_km=52.0, source_citation="IPCC 2006 Tier 1"),
    EmissionFactor(mode="andong", g_co2_per_km=0.0, source_citation="IPCC 2006 Tier 1"),
    EmissionFactor(mode="becak", g_co2_per_km=0.0, source_citation="IPCC 2006 Tier 1"),
    EmissionFactor(mode="walk", g_co2_per_km=0.0, source_citation="IPCC 2006 Tier 1"),
]


async def upsert_emission_factors(session: AsyncSession, factors: list[EmissionFactor]) -> int:
    rows = [
        {
            "mode": factor.mode,
            "g_co2_per_km": factor.g_co2_per_km,
            "source_citation": factor.source_citation,
        }
        for factor in factors
    ]
    if not rows:
        return 0

    stmt = pg_insert(EmissionFactorRow).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[EmissionFactorRow.mode],
        set_={
            "g_co2_per_km": stmt.excluded.g_co2_per_km,
            "source_citation": stmt.excluded.source_citation,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


def _point_lon_lat(feature: Feature) -> tuple[float, float] | None:
    coords = feature.geometry.get("coordinates")
    if not coords or len(coords) < 2:
        return None
    return coords[0], coords[1]


async def upsert_poi(session: AsyncSession, features: list[Feature], source: Dataset) -> int:
    rows = []
    for feature in features:
        point = _point_lon_lat(feature)
        if point is None:
            continue
        lon, lat = point
        props = feature.properties
        rows.append(
            {
                "external_id": feature.external_id,
                "source": source,
                "nama_tempat": props.get("nama_tempat") or props.get("title"),
                "kategori": props.get("kategori_tempat") or props.get("jenis_tempat"),
                "jam_buka": props.get("jam_buka"),
                "jam_tutup": props.get("jam_tutup"),
                "harga_rata_rata": props.get("harga_rata_rata"),
                "foto_url": props.get("foto_tempat") or props.get("foto_struk"),
                "raw": props,
                "geom": func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
            }
        )
    if not rows:
        return 0

    stmt = pg_insert(Poi).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Poi.external_id],
        set_={
            "nama_tempat": stmt.excluded.nama_tempat,
            "kategori": stmt.excluded.kategori,
            "jam_buka": stmt.excluded.jam_buka,
            "jam_tutup": stmt.excluded.jam_tutup,
            "harga_rata_rata": stmt.excluded.harga_rata_rata,
            "foto_url": stmt.excluded.foto_url,
            "raw": stmt.excluded.raw,
            "geom": stmt.excluded.geom,
            "fetched_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


# MAPID's halte layer carries no operator column — every row is
# TIPE_1=TRANSPORTASI / TIPE_2=HALTE — so the operator is read off the name,
# which is the only place the network is actually recorded. Anything the name
# does not identify stays the layer's own scope rather than being assigned to
# TransJogja on a guess.
_TRANSJOGJA_MARKERS = ("TRANS JOGJA", "TRANSJOGJA", "TRANS BONBIN", "TJ ", "TPB ")


def _stop_operator(name: str, default: str) -> str:
    upper = name.upper()
    if any(marker in upper for marker in _TRANSJOGJA_MARKERS) or upper.startswith(("TJ", "TPB")):
        return "TransJogja"
    return default


def _clean_stop_name(raw_name: str) -> str:
    """Drop the mojibake the survey sheet carries and collapse whitespace.

    Several names end in a run of literal `?` where Javanese script was lost in
    an encoding round-trip upstream (e.g. `HALTE IREDA. ??????????`). Rendering
    that in a search result is worse than rendering nothing, and it is garbage
    rather than data, so it goes. The Latin part of the name is untouched —
    including its upstream casing.
    """
    cleaned = re.sub(r"[?]{2,}", "", raw_name)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned)
    cleaned = re.sub(r"[\s.,\-(]+$", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


async def upsert_transit_stops(
    session: AsyncSession,
    features: list[Feature],
    *,
    mode: str = "bus",
    source: str = "mapid_geoserver",
    default_operator: str = "Halte Kota Yogyakarta",
) -> int:
    rows = []
    for feature in features:
        point = _point_lon_lat(feature)
        if point is None:
            continue
        lon, lat = point
        props = feature.properties
        name = (
            _clean_stop_name(
                str(props.get("NAMA") or props.get("nama") or props.get("title") or "")
            )
            or "Halte"
        )
        rows.append(
            {
                "external_id": feature.external_id,
                "name": name,
                "mode": mode,
                "operator": _stop_operator(name, default_operator),
                "raw": props,
                "source": source,
                "geom": func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
            }
        )
    if not rows:
        return 0

    stmt = pg_insert(TransitStop).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[TransitStop.external_id],
        set_={
            "name": stmt.excluded.name,
            "mode": stmt.excluded.mode,
            "operator": stmt.excluded.operator,
            "raw": stmt.excluded.raw,
            "source": stmt.excluded.source,
            "geom": stmt.excluded.geom,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


def _first_media(props: dict) -> str | None:
    medias = props.get("medias")
    if isinstance(medias, list) and medias and isinstance(medias[0], str):
        return medias[0]
    return None


def _surveyed_at(props: dict) -> datetime | None:
    stamp = props.get("created_at")
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def upsert_pangkalan(
    session: AsyncSession,
    features: list[Feature],
    *,
    stand_type: str,
    source: str,
) -> int:
    """Mirror surveyed andong/becak stands.

    `fare_base` / `fare_per_km` are left NULL: a community activity post
    records where a stand is, not what it charges, and `fetch_network_data`
    only lifts a pangkalan into the routing graph once both are known. A stand
    ingested here is therefore a real marker on the map and not yet a
    connector — which is the honest state of it.
    """
    rows = []
    for feature in features:
        point = _point_lon_lat(feature)
        if point is None:
            continue
        lon, lat = point
        props = feature.properties
        rows.append(
            {
                "external_id": feature.external_id,
                "type": stand_type,
                "name": str(props.get("title") or props.get("nama") or "").strip() or None,
                "photo_url": _first_media(props),
                "surveyor": props.get("user_full_name") or props.get("user_name"),
                "surveyed_at": _surveyed_at(props),
                "raw": props,
                "source": source,
                "geom": func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
            }
        )
    if not rows:
        return 0

    stmt = pg_insert(Pangkalan).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Pangkalan.external_id],
        set_={
            "type": stmt.excluded.type,
            "name": stmt.excluded.name,
            "photo_url": stmt.excluded.photo_url,
            "surveyor": stmt.excluded.surveyor,
            "surveyed_at": stmt.excluded.surveyed_at,
            "raw": stmt.excluded.raw,
            "source": stmt.excluded.source,
            "geom": stmt.excluded.geom,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def upsert_properti(session: AsyncSession, features: list[Feature]) -> int:
    rows = []
    for feature in features:
        point = _point_lon_lat(feature)
        if point is None:
            continue
        lon, lat = point
        props = feature.properties
        rows.append(
            {
                "external_id": feature.external_id,
                "kategori_properti": props.get("kategori_properti"),
                "jenis_properti": props.get("jenis_properti"),
                "alamat": props.get("alamat"),
                "foto_url": props.get("foto_tampak_depan") or props.get("foto_spanduk"),
                "raw": props,
                "geom": func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
            }
        )
    if not rows:
        return 0

    stmt = pg_insert(Properti).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Properti.external_id],
        set_={
            "kategori_properti": stmt.excluded.kategori_properti,
            "jenis_properti": stmt.excluded.jenis_properti,
            "alamat": stmt.excluded.alamat,
            "foto_url": stmt.excluded.foto_url,
            "raw": stmt.excluded.raw,
            "geom": stmt.excluded.geom,
            "fetched_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)
