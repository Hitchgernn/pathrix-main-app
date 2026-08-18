from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransitStop(Base):
    __tablename__ = "transit_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None]
    name: Mapped[str]
    mode: Mapped[str]
    operator: Mapped[str]
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    source: Mapped[str]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (CheckConstraint("mode IN ('bus','rail','airport_rail')"),)


class TransitRoute(Base):
    __tablename__ = "transit_routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    operator: Mapped[str]
    mode: Mapped[str]
    headway_min: Mapped[float]
    fare_idr: Mapped[int]
    geom: Mapped[str | None] = mapped_column(Geometry("LINESTRING", srid=4326))
    source: Mapped[str]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RouteStop(Base):
    __tablename__ = "route_stops"

    route_id: Mapped[int] = mapped_column(ForeignKey("transit_routes.id"), primary_key=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("transit_stops.id"))
    seq: Mapped[int] = mapped_column(primary_key=True)
    travel_time_from_prev_s: Mapped[int | None]


class Pangkalan(Base):
    __tablename__ = "pangkalan"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    name: Mapped[str | None]
    operating_hours: Mapped[str | None]
    fare_base: Mapped[int | None]
    fare_per_km: Mapped[int | None]
    photo_url: Mapped[str | None]
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    surveyor: Mapped[str | None]
    surveyed_at: Mapped[datetime | None]
    source: Mapped[str] = mapped_column(default="field_survey")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (CheckConstraint("type IN ('andong','becak')"),)


class Poi(Base):
    __tablename__ = "poi"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(unique=True)
    source: Mapped[str]
    nama_tempat: Mapped[str | None]
    kategori: Mapped[str | None]
    jam_buka: Mapped[str | None]
    jam_tutup: Mapped[str | None]
    harga_rata_rata: Mapped[int | None]
    foto_url: Mapped[str | None]
    raw: Mapped[dict] = mapped_column(JSONB)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("source IN ('menugo','struckgo','activities')"),
        Index("ix_poi_source", "source"),
    )


class Properti(Base):
    __tablename__ = "properti"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(unique=True)
    kategori_properti: Mapped[str | None]
    jenis_properti: Mapped[str | None]
    alamat: Mapped[str | None]
    foto_url: Mapped[str | None]
    raw: Mapped[dict] = mapped_column(JSONB)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WalkNode(Base):
    __tablename__ = "walk_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))


class WalkEdge(Base):
    __tablename__ = "walk_edges"

    u: Mapped[int] = mapped_column(primary_key=True)
    v: Mapped[int] = mapped_column(primary_key=True)
    length_m: Mapped[float]
    geom: Mapped[str | None] = mapped_column(Geometry("LINESTRING", srid=4326))


class Isochrone(Base):
    __tablename__ = "isochrones"

    stop_id: Mapped[int] = mapped_column(ForeignKey("transit_stops.id"), primary_key=True)
    minutes: Mapped[int] = mapped_column(primary_key=True)
    geom: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326))
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    mode: Mapped[str] = mapped_column(primary_key=True)
    g_co2_per_km: Mapped[float]
    source_citation: Mapped[str]
