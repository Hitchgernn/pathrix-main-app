import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.data.repository import ViewportDataType, query_features_in_viewport
from app.data.schema import Isochrone
from app.models.geo import BBox
from app.models.layers import IsochroneOut, LayerMeta
from app.models.mapid import Feature

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
        name="Transit (TransJogja/KRL/YIA)",
        queryable=False,
        description="Bus, rail, and airport rail stops and routes. Feature query not wired yet.",
    ),
    LayerMeta(
        id="pangkalan",
        name="Andong/Becak",
        queryable=False,
        description="First/last-mile andong and becak stands. Feature query not wired yet.",
    ),
]

_QUERYABLE_LAYERS: set[ViewportDataType] = {"poi", "properti"}


@router.get("/layers", response_model=list[LayerMeta])
async def list_layers() -> list[LayerMeta]:
    return LAYER_CATALOGUE


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
