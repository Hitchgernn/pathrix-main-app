from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.schema import Poi, Properti
from app.models.mapid import Dataset, Feature


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
