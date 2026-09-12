from typing import NamedTuple

from shapely import Polygon, box
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.mapid import MapidClient
from app.data.osm import WalkNetworkFetcher
from app.data.repository import (
    upsert_pangkalan,
    upsert_poi,
    upsert_properti,
    upsert_transit_stops,
    upsert_walk_network,
)
from app.models.mapid import Dataset, Feature

# The `activities` endpoint answers at most this many posts, newest first, and
# says nothing about it: there is no `pagination` block, `meta.total` reports
# only what was returned, and `offset` is ignored, so a capped response is
# indistinguishable from a complete one. Verified against the live API — a
# Yogyakarta-wide query and a Java-wide query both return exactly 60 with no ids in
# common, while a 100 m box returns 5. The three `*go` missions paginate
# properly and need none of this.
ACTIVITIES_RESPONSE_CAP = 60

# Measured against the live DIY study area, where the feed holds ~963 posts:
# depth 4 recovers 561 with 5 tiles still capped, depth 7 recovers 957 with 2,
# and depth 8 recovers all 963 with none — depths 9 and 10 return the identical
# set, so 8 is where it converges rather than where we gave up. Only dense
# tiles split, so this costs 77 requests and about 4 s, not 4^8. A tile still
# at the cap here is reported, never silently dropped: posts stacked on one
# coordinate cannot be separated by any amount of subdivision.
ACTIVITIES_MAX_TILE_DEPTH = 8


class ActivityHarvest(NamedTuple):
    features: list[Feature]
    #: Tiles that still answered at the cap at maximum depth — each one may be
    #: hiding older posts. 0 means the harvest is provably complete.
    capped_tiles: int


class EtlResult(NamedTuple):
    rows: int
    capped_tiles: int


def _subdivide(area: Polygon) -> list[Polygon]:
    """Quarter a polygon, clipped back to its own shape.

    Clipping rather than returning the four bare quadrants keeps a non-
    rectangular study area from pulling in posts beyond its edges; a quarter
    that splits into several pieces is enqueued as each piece.
    """
    min_lon, min_lat, max_lon, max_lat = area.bounds
    mid_lon = (min_lon + max_lon) / 2
    mid_lat = (min_lat + max_lat) / 2
    quarters = (
        box(min_lon, min_lat, mid_lon, mid_lat),
        box(mid_lon, min_lat, max_lon, mid_lat),
        box(min_lon, mid_lat, mid_lon, max_lat),
        box(mid_lon, mid_lat, max_lon, max_lat),
    )

    pieces: list[Polygon] = []
    for quarter in quarters:
        clipped = area.intersection(quarter)
        if clipped.is_empty:
            continue
        for part in getattr(clipped, "geoms", [clipped]):
            if isinstance(part, Polygon) and not part.is_empty:
                pieces.append(part)
    return pieces


async def fetch_activities_in_full(
    client: MapidClient,
    polygon: Polygon,
    *,
    cap: int = ACTIVITIES_RESPONSE_CAP,
    max_depth: int = ACTIVITIES_MAX_TILE_DEPTH,
) -> ActivityHarvest:
    """Every activity inside `polygon`, by tiling around the response cap.

    A response that comes back at the cap is assumed truncated and its area is
    quartered; one that comes back short is complete and is taken as-is. Posts
    are keyed by id, so the overlap between adjacent tiles costs requests, not
    duplicates.
    """
    found: dict[str, Feature] = {}
    capped_tiles = 0
    queue: list[tuple[Polygon, int]] = [(polygon, 0)]

    while queue:
        area, depth = queue.pop()
        page = await client.fetch_missions("activities", area, limit=cap, offset=0)
        for feature in page.features:
            found.setdefault(feature.external_id, feature)

        if len(page.features) < cap:
            continue
        if depth >= max_depth:
            capped_tiles += 1
            continue
        queue.extend((piece, depth + 1) for piece in _subdivide(area))

    return ActivityHarvest(list(found.values()), capped_tiles)


async def run_etl(
    client: MapidClient,
    session: AsyncSession,
    dataset: Dataset,
    polygon: Polygon,
    page_size: int = 100,
) -> EtlResult:
    if dataset == "activities":
        harvest = await fetch_activities_in_full(client, polygon)
        return EtlResult(await upsert_poi(session, harvest.features, dataset), harvest.capped_tiles)

    total = 0
    offset = 0
    while True:
        page = await client.fetch_missions(dataset, polygon, limit=page_size, offset=offset)
        if dataset == "propertigo":
            total += await upsert_properti(session, page.features)
        else:
            total += await upsert_poi(session, page.features, dataset)

        if not page.has_more or not page.features:
            break
        offset += page_size

    return EtlResult(total, 0)


async def run_transit_stop_etl(
    client: MapidClient,
    session: AsyncSession,
    layer_id: str,
    project_id: str,
    *,
    mode: str = "bus",
) -> int:
    """Mirror one MAPID geoserver point layer into `transit_stops`.

    No pagination loop, unlike `run_etl`: the geoserver hands back the whole
    FeatureCollection in a single response.

    `source` names the layer, not just the host. Two editions of the same
    survey (the project carries a 2024 and a 2025 halte layer, identical
    geometry under different feature uuids) are otherwise indistinguishable
    once mirrored, and nothing here can tell that a second ingest re-surveyed
    the same shelters rather than found new ones.
    """
    layer = await client.fetch_layer(layer_id, project_id)
    return await upsert_transit_stops(
        session, layer.features, mode=mode, source=f"mapid_geoserver:{layer_id}"
    )


# Community activity posts are free text, so the classifier is deliberately
# narrow: a title that opens with "halte" is a shelter, one that names becak or
# andong is a stand, and everything else stays where the mission ETL put it
# (a market, a crowding observation — a POI, not infrastructure). Andong has no
# marker yet in the surveyed data; it is listed because the table models both.
_BECAK_MARKERS = ("becak",)
_ANDONG_MARKERS = ("andong", "delman")


def _classify_activity(feature: Feature) -> str | None:
    title = str(feature.properties.get("title") or "").strip().lower()
    if title.startswith("halte"):
        return "halte"
    if any(marker in title for marker in _ANDONG_MARKERS):
        return "andong"
    if any(marker in title for marker in _BECAK_MARKERS):
        return "becak"
    return None


async def run_activity_survey_etl(
    client: MapidClient,
    session: AsyncSession,
    polygon: Polygon,
) -> dict[str, int]:
    """Lift transport infrastructure out of the `activities` mission feed.

    The feed is a mixed bag — halte condition surveys, becak stands, market
    crowding notes — and `run_etl` mirrors all of it into `poi` verbatim. This
    is the second pass that files the infrastructure under the tables that
    model it, so a halte draws as a halte rather than as an anonymous dot.
    Rows stay in `poi` as well: that is the unedited record of what was posted.
    """
    halte: list[Feature] = []
    becak: list[Feature] = []
    andong: list[Feature] = []
    buckets = {"halte": halte, "becak": becak, "andong": andong}

    harvest = await fetch_activities_in_full(client, polygon)
    for feature in harvest.features:
        kind = _classify_activity(feature)
        if kind is not None:
            buckets[kind].append(feature)

    counts = {
        "halte": await upsert_transit_stops(
            session,
            halte,
            source="mapid_activities",
            default_operator="Survei komunitas MAPID",
        ),
        "becak": await upsert_pangkalan(
            session, becak, stand_type="becak", source="mapid_activities"
        ),
        "andong": await upsert_pangkalan(
            session, andong, stand_type="andong", source="mapid_activities"
        ),
        # Surfaced, not swallowed: a non-zero count means the feed still hid
        # posts from us and the mirror is the newest slice, not the whole.
        "capped_tiles": harvest.capped_tiles,
    }
    return counts


async def run_walk_network_etl(
    fetcher: WalkNetworkFetcher, session: AsyncSession, polygon: Polygon
) -> tuple[int, int]:
    nodes, edges = await fetcher.fetch(polygon)
    return await upsert_walk_network(session, nodes, edges)
