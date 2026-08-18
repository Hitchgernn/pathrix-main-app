from shapely import Polygon
from sqlalchemy import select

from app.data.etl import run_etl
from app.data.repository import upsert_poi
from app.data.schema import Poi
from app.models.mapid import Feature, MissionPage

_POLYGON = Polygon([(110.2, -7.9), (110.5, -7.9), (110.5, -7.7), (110.2, -7.7)])


async def test_upsert_poi_is_idempotent_and_updates_on_conflict(db_session):
    feature = Feature(
        external_id="abc123",
        properties={"nama_tempat": "Warung A", "jam_buka": "08:00"},
        geometry={"type": "Point", "coordinates": [110.37, -7.80]},
    )
    count_first = await upsert_poi(db_session, [feature], "menugo")
    assert count_first == 1

    updated_feature = Feature(
        external_id="abc123",
        properties={"nama_tempat": "Warung A Updated", "jam_buka": "09:00"},
        geometry={"type": "Point", "coordinates": [110.37, -7.80]},
    )
    count_second = await upsert_poi(db_session, [updated_feature], "menugo")
    assert count_second == 1

    result = await db_session.execute(select(Poi).where(Poi.external_id == "abc123"))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].nama_tempat == "Warung A Updated"
    assert rows[0].jam_buka == "09:00"


class _PagingFakeClient:
    def __init__(self) -> None:
        self._pages = {
            0: MissionPage(
                features=[
                    Feature(
                        external_id="p1",
                        properties={"nama_tempat": "A"},
                        geometry={"type": "Point", "coordinates": [110.30, -7.80]},
                    )
                ],
                has_more=True,
            ),
            1: MissionPage(
                features=[
                    Feature(
                        external_id="p2",
                        properties={"nama_tempat": "B"},
                        geometry={"type": "Point", "coordinates": [110.31, -7.81]},
                    )
                ],
                has_more=False,
            ),
        }

    async def fetch_missions(self, dataset, polygon, *, limit=1, offset=0, **_):
        return self._pages.get(offset // limit, MissionPage(features=[], has_more=False))

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return ""


async def test_run_etl_paginates_to_exhaustion_and_upserts_all_pages(db_session):
    client = _PagingFakeClient()
    total = await run_etl(client, db_session, "menugo", _POLYGON, page_size=1)
    assert total == 2

    result = await db_session.execute(select(Poi.external_id))
    assert {row[0] for row in result.all()} == {"p1", "p2"}
