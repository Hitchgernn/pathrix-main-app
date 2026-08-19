import json
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.schema import EmissionFactor as EmissionFactorRow
from app.data.schema import Pangkalan, Poi, Properti, RouteStop, TransitRoute, TransitStop
from app.models.geo import BBox
from app.models.mapid import Dataset, Feature
from app.models.network import NetworkData, PangkalanRow, RouteRow, RouteStopRow, StopRow
from app.models.routing import EmissionFactor

ViewportDataType = Literal["poi", "properti"]

_VIEWPORT_TABLES = {"poi": Poi, "properti": Properti}


async def query_features_in_viewport(
    session: AsyncSession, data_type: ViewportDataType, bbox: BBox, limit: int = 50
) -> list[Feature]:
    table = _VIEWPORT_TABLES[data_type]
    envelope = func.ST_MakeEnvelope(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326)
    stmt = (
        select(table.external_id, table.raw, func.ST_AsGeoJSON(table.geom).label("geom_json"))
        .where(func.ST_Intersects(table.geom, envelope))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        Feature(external_id=row.external_id, properties=row.raw, geometry=json.loads(row.geom_json))
        for row in result
    ]


async def fetch_network_data(session: AsyncSession) -> NetworkData:
    stop_rows = await session.execute(
        select(TransitStop.id, func.ST_X(TransitStop.geom), func.ST_Y(TransitStop.geom))
    )
    route_rows = await session.execute(
        select(TransitRoute.id, TransitRoute.headway_min, TransitRoute.fare_idr)
    )
    route_stop_rows = await session.execute(
        select(
            RouteStop.route_id, RouteStop.stop_id, RouteStop.seq, RouteStop.travel_time_from_prev_s
        )
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

    return NetworkData(
        stops=[StopRow(id=r[0], lon=r[1], lat=r[2]) for r in stop_rows],
        routes=[RouteRow(id=r[0], headway_min=r[1], fare_idr=r[2]) for r in route_rows],
        route_stops=[
            RouteStopRow(route_id=r[0], stop_id=r[1], seq=r[2], travel_time_from_prev_s=r[3])
            for r in route_stop_rows
        ],
        pangkalan=[
            PangkalanRow(id=r[0], type=r[1], lon=r[2], lat=r[3], fare_base=r[4], fare_per_km=r[5])
            for r in pangkalan_rows
        ],
    )


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
