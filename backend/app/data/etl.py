from shapely import Polygon
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.mapid import MapidClient
from app.data.osm import WalkNetworkFetcher
from app.data.repository import upsert_poi, upsert_properti, upsert_walk_network
from app.models.mapid import Dataset


async def run_etl(
    client: MapidClient,
    session: AsyncSession,
    dataset: Dataset,
    polygon: Polygon,
    page_size: int = 100,
) -> int:
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

    return total


async def run_walk_network_etl(
    fetcher: WalkNetworkFetcher, session: AsyncSession, polygon: Polygon
) -> tuple[int, int]:
    nodes, edges = await fetcher.fetch(polygon)
    return await upsert_walk_network(session, nodes, edges)
