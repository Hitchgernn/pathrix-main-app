import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.data.repository import (
    ViewportDataType,
    fetch_estimated_transit_segments,
    fetch_manually_reviewed_stop_external_ids,
    fetch_stop_departures,
    query_features_in_viewport,
)
from app.data.schema import Isochrone
from app.models.geo import BBox
from app.models.layers import IsochroneOut, LayerMeta
from app.models.mapid import Feature
from app.models.routing import StopDeparture

router = APIRouter(prefix="/api")

# Grounded in the tables that actually exist (data/schema.py), not an unverified
# PRD enumeration — proposal_pathrix.md / PRD_AI_TOD_Navigator_Yogyakarta.md
# aren't in this repo.
LAYER_CATALOGUE: list[LayerMeta] = [
    LayerMeta(
        id="poi",
        name="Kuliner & Aktivitas (MAPID)",
        queryable=True,
        description="Menu Go / Struk Go / Activities mission mirror.",
    ),
    LayerMeta(
        id="properti",
        name="Properti (MAPID)",
        queryable=True,
        description="Properti Go mission mirror.",
    ),
    LayerMeta(
        id="transit",
        name="Halte & Stasiun (TransJogja/KRL/YIA)",
        queryable=True,
        description="Halte mirrored from the MAPID geoserver; rail stops once surveyed.",
    ),
    LayerMeta(
        id="pangkalan",
        name="Andong/Becak",
        queryable=True,
        description="First/last-mile andong and becak stands, from the MAPID activity survey.",
    ),
]

_QUERYABLE_LAYERS: set[ViewportDataType] = {"poi", "properti", "transit", "pangkalan"}


@router.get("/layers", response_model=list[LayerMeta])
async def list_layers() -> list[LayerMeta]:
    return LAYER_CATALOGUE


@router.get("/layers/manual-reviews", response_model=list[str])
async def manually_reviewed_stops(session: AsyncSession = Depends(get_session)) -> list[str]:
    """external_ids of stops whose Activity match came from human review, not
    an automated match — the frontend marks these with a real pin instead of
    the flat circle every other mission-layer feature gets."""
    return await fetch_manually_reviewed_stop_external_ids(session)


@router.get("/transit/estimated-segments")
async def estimated_transit_segments(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """OSM driving estimates for adjacent, Activity-backed bus stop pairs."""
    return await fetch_estimated_transit_segments(
        session, BBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    )


@router.get("/layers/{layer_id}/features", response_model=list[Feature])
async def layer_features(
    layer_id: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[Feature]:
    if layer_id not in _QUERYABLE_LAYERS:
        raise HTTPException(
            status_code=501, detail=f"layer {layer_id!r} feature query not implemented yet"
        )
    bbox = BBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    return await query_features_in_viewport(session, layer_id, bbox, limit)


@router.get(
    "/transit/stops/{external_stop_id}/departures",
    response_model=list[StopDeparture],
)
async def stop_departures(
    external_stop_id: str,
    after_local: str | None = Query(
        default=None,
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$",
    ),
    limit: int = Query(default=8, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[StopDeparture]:
    return await fetch_stop_departures(
        session,
        external_stop_id,
        after_local=after_local,
        limit=limit,
    )


@router.get("/isochrone/{stop_id}", response_model=IsochroneOut)
async def get_isochrone(
    stop_id: int, minutes: int, session: AsyncSession = Depends(get_session)
) -> IsochroneOut:
    stmt = select(func.ST_AsGeoJSON(Isochrone.geom)).where(
        Isochrone.stop_id == stop_id, Isochrone.minutes == minutes
    )
    geom_json = await session.scalar(stmt)
    if geom_json is None:
        raise HTTPException(status_code=404, detail="isochrone not computed for this stop/minutes")
    return IsochroneOut(stop_id=stop_id, minutes=minutes, geometry=json.loads(geom_json))
