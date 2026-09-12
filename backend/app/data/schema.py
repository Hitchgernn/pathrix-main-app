from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransitStop(Base):
    __tablename__ = "transit_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Unique because mirrored sources (MAPID geoserver today, a survey sheet
    # later) are re-ingested repeatedly and must upsert, not duplicate. Still
    # nullable: a hand-entered stop has no upstream id.
    external_id: Mapped[str | None] = mapped_column(unique=True)
    name: Mapped[str]
    mode: Mapped[str]
    operator: Mapped[str]
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    # Upstream attributes kept verbatim, same contract as poi.raw / properti.raw:
    # /api/layers/transit/features hands them to the client untouched.
    raw: Mapped[dict | None] = mapped_column(JSONB)
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


class TransitScheduleImport(Base):
    """One reversible, idempotent import of normalized timetable data."""

    __tablename__ = "transit_schedule_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_key: Mapped[str] = mapped_column(unique=True)
    source_digest: Mapped[str]
    source_path: Mapped[str]
    status: Mapped[str]
    effective_from: Mapped[date | None]
    effective_until: Mapped[date | None]
    freshness_as_of: Mapped[date | None]
    freshness_status: Mapped[str]
    report: Mapped[dict] = mapped_column(JSONB)
    imported_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('applying','complete','failed','rolled_back')"),
        CheckConstraint("freshness_status IN ('verified','unverified','stale')"),
    )


class TransitScheduleRoute(Base):
    """Records route ownership so a schedule batch can be rolled back safely."""

    __tablename__ = "transit_schedule_routes"

    schedule_import_id: Mapped[int] = mapped_column(
        ForeignKey("transit_schedule_imports.id", ondelete="CASCADE"), primary_key=True
    )
    route_id: Mapped[int] = mapped_column(
        ForeignKey("transit_routes.id", ondelete="CASCADE"), primary_key=True
    )
    source_route_id: Mapped[str]
    created_route: Mapped[bool]


class TransitServiceProfile(Base):
    __tablename__ = "transit_service_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_import_id: Mapped[int] = mapped_column(
        ForeignKey("transit_schedule_imports.id", ondelete="CASCADE")
    )
    route_id: Mapped[int] = mapped_column(ForeignKey("transit_routes.id", ondelete="CASCADE"))
    basis: Mapped[str]
    service_start_local: Mapped[str | None]
    service_end_local: Mapped[str | None]
    service_end_alternate_local: Mapped[str | None]
    headway_min_minutes: Mapped[float | None]
    headway_max_minutes: Mapped[float | None]
    headway_is_approximate: Mapped[bool]
    fleet_count: Mapped[int | None]
    notes: Mapped[str | None]
    provenance: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "schedule_import_id", "route_id", "basis", name="uq_schedule_profile_batch_route_basis"
        ),
    )


class TransitTrip(Base):
    __tablename__ = "transit_trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_import_id: Mapped[int] = mapped_column(
        ForeignKey("transit_schedule_imports.id", ondelete="CASCADE")
    )
    route_id: Mapped[int] = mapped_column(ForeignKey("transit_routes.id", ondelete="CASCADE"))
    external_id: Mapped[str]
    train_number: Mapped[str | None]
    service_class: Mapped[str | None]
    service_days: Mapped[str | None]
    is_estimated: Mapped[bool]
    provenance: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "schedule_import_id", "external_id", name="uq_transit_trip_batch_external"
        ),
    )


class TransitStopTime(Base):
    __tablename__ = "transit_stop_times"

    trip_id: Mapped[int] = mapped_column(
        ForeignKey("transit_trips.id", ondelete="CASCADE"), primary_key=True
    )
    stop_id: Mapped[int] = mapped_column(ForeignKey("transit_stops.id"))
    seq: Mapped[int] = mapped_column(primary_key=True)
    scheduled_time_local: Mapped[str]
    day_offset: Mapped[int]
    is_estimated: Mapped[bool]


class Pangkalan(Base):
    __tablename__ = "pangkalan"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Same contract as transit_stops: unique so a re-ingested survey upserts,
    # nullable because a hand-entered stand has no upstream id.
    external_id: Mapped[str | None] = mapped_column(unique=True)
    type: Mapped[str]
    name: Mapped[str | None]
    operating_hours: Mapped[str | None]
    fare_base: Mapped[int | None]
    fare_per_km: Mapped[int | None]
    photo_url: Mapped[str | None]
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    surveyor: Mapped[str | None]
    surveyed_at: Mapped[datetime | None]
    raw: Mapped[dict | None] = mapped_column(JSONB)
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
