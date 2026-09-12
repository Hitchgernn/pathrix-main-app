from math import ceil, sqrt

from shapely import Polygon
from shapely.geometry import Point
from sqlalchemy import select

from app.data.etl import (
    ACTIVITIES_RESPONSE_CAP,
    fetch_activities_in_full,
    run_activity_survey_etl,
    run_etl,
    run_transit_stop_etl,
)
from app.data.mapid import FakeMapidClient
from app.data.repository import (
    query_features_in_viewport,
    search_places,
    upsert_poi,
    upsert_transit_stops,
)
from app.data.schema import Pangkalan, Poi, TransitStop
from app.models.geo import BBox
from app.models.mapid import Feature, LayerFeatures, MissionPage

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
    assert total.rows == 2
    # Only `activities` is capped; a paginating dataset is never tiled.
    assert total.capped_tiles == 0

    result = await db_session.execute(select(Poi.external_id))
    assert {row[0] for row in result.all()} == {"p1", "p2"}


def _halte(external_id: str, name: str, lon: float = 110.39, lat: float = -7.83) -> Feature:
    return Feature(
        external_id=external_id,
        properties={"fid": 1, "NAMA": name, "TIPE_2": "HALTE", "ALAMAT": "JL. X"},
        geometry={"type": "Point", "coordinates": [lon, lat]},
    )


async def test_upsert_transit_stops_cleans_names_and_reads_the_operator_off_them(db_session):
    count = await upsert_transit_stops(
        db_session,
        [
            _halte("h1", "TRANS JOGJA TERMINAL GIWANGAN"),
            _halte("h2", "HALTE IREDA. ??????????", lon=110.37, lat=-7.81),
            _halte("h3", "NGABEAN", lon=110.35, lat=-7.80),
        ],
    )
    assert count == 3

    rows = (await db_session.execute(select(TransitStop))).scalars().all()
    by_id = {row.external_id: row for row in rows}
    assert by_id["h1"].operator == "TransJogja"
    # The trailing run of `?` is lost Javanese script, not a name.
    assert by_id["h2"].name == "HALTE IREDA"
    # Nothing in the name claims a network, so none is assigned.
    assert by_id["h3"].operator == "Halte Kota Yogyakarta"
    assert all(row.mode == "bus" and row.source == "mapid_geoserver" for row in rows)
    assert by_id["h1"].raw["ALAMAT"] == "JL. X"


async def test_upsert_transit_stops_upserts_on_re_ingest(db_session):
    await upsert_transit_stops(db_session, [_halte("h1", "HALTE LAMA")])
    await upsert_transit_stops(db_session, [_halte("h1", "HALTE BARU", lon=110.40, lat=-7.84)])

    rows = (await db_session.execute(select(TransitStop))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "HALTE BARU"


async def test_run_transit_stop_etl_mirrors_a_geoserver_layer_into_the_viewport_query(db_session):
    client = FakeMapidClient(
        {},
        layers={
            "layer-1": LayerFeatures(
                layer_id="layer-1",
                layer_name="HALTE DI KOTA YOGYAKARTA TAHUN 2025",
                features=[_halte("h1", "TJ MANGKUBUMI 1"), _halte("h2", "MALIOBORO 2 KEPATIHAN")],
            )
        },
    )
    total = await run_transit_stop_etl(client, db_session, "layer-1", "project-1")
    assert total == 2

    # Provenance names the layer: the project carries two editions of the same
    # halte survey, and `mapid_geoserver` alone would not say which one landed.
    sources = (await db_session.execute(select(TransitStop.source))).scalars().all()
    assert set(sources) == {"mapid_geoserver:layer-1"}

    features = await query_features_in_viewport(
        db_session,
        "transit",
        BBox(min_lon=110.3, min_lat=-7.9, max_lon=110.5, max_lat=-7.7),
    )
    assert {f.external_id for f in features} == {"h1", "h2"}
    assert features[0].geometry["type"] == "Point"


def _activity(external_id: str, title: str, lon: float = 110.39, lat: float = -7.80) -> Feature:
    return Feature(
        external_id=external_id,
        properties={
            "title": title,
            "medias": ["https://cdn.example/photo.jpg"],
            "user_full_name": "Surveyor A",
            "created_at": "2026-08-30T03:04:16.970Z",
        },
        geometry={"type": "Point", "coordinates": [lon, lat]},
    )


class _ActivityClient:
    """Only `activities` is populated — the survey pass reads nothing else."""

    def __init__(self, features: list[Feature]) -> None:
        self._features = features

    async def fetch_missions(self, dataset, polygon, *, limit=100, offset=0, **_):
        if dataset != "activities" or offset:
            return MissionPage(features=[], has_more=False)
        return MissionPage(features=self._features, has_more=False)

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return ""


async def test_activity_survey_etl_files_infrastructure_and_leaves_the_rest(db_session):
    client = _ActivityClient(
        [
            _activity("a1", "Halte UIN Sunan Kalijaga A"),
            _activity("a2", "Halte UIN Sunan Kalijaga B", lat=-7.8004),
            _activity("a3", "Pangkalan Becak Alun-Alun Utara", lon=110.3646),
            _activity("a4", "Titik Kumpul Becak Pasar Serangan", lon=110.3544),
            # Neither a shelter nor a stand: a market and a crowding note stay
            # in poi, where the mission ETL already put them.
            _activity("a5", "Pasar Lempuyangan", lon=110.3736),
            _activity("a6", "Kepadatan di titik nol malioboro", lon=110.3647),
        ]
    )

    counts = await run_activity_survey_etl(client, db_session, _POLYGON)
    assert counts == {"halte": 2, "becak": 2, "andong": 0, "capped_tiles": 0}

    stops = (await db_session.execute(select(TransitStop))).scalars().all()
    assert {s.name for s in stops} == {"Halte UIN Sunan Kalijaga A", "Halte UIN Sunan Kalijaga B"}
    # A community post says nothing about the operator, so it is not assigned one.
    assert {s.operator for s in stops} == {"Survei komunitas MAPID"}
    assert {s.source for s in stops} == {"mapid_activities"}

    stands = (await db_session.execute(select(Pangkalan))).scalars().all()
    assert {p.type for p in stands} == {"becak"}
    assert {p.surveyor for p in stands} == {"Surveyor A"}
    assert all(p.photo_url == "https://cdn.example/photo.jpg" for p in stands)
    assert all(p.surveyed_at is not None for p in stands)
    # Where a stand charges is not what an activity post records, and
    # fetch_network_data only routes a pangkalan once both fares are known.
    assert all(p.fare_base is None and p.fare_per_km is None for p in stands)


async def test_activity_survey_etl_upserts_rather_than_duplicating(db_session):
    client = _ActivityClient([_activity("a1", "Halte UIN Sunan Kalijaga A")])
    await run_activity_survey_etl(client, db_session, _POLYGON)
    await run_activity_survey_etl(client, db_session, _POLYGON)

    stops = (await db_session.execute(select(TransitStop))).scalars().all()
    assert len(stops) == 1


async def test_a_halte_filed_out_of_activities_is_not_also_a_poi(db_session):
    """One shelter, one result — in the search box and on the map.

    The survey pass leaves the original `activities` row in `poi` as the record
    of what was posted, so both tables hold it; neither surface may show it
    twice.
    """
    activity = _activity("a1", "Halte Gembira Loka A", lon=110.4001, lat=-7.8022)
    await upsert_poi(db_session, [activity], "activities")
    await upsert_transit_stops(db_session, [activity], source="mapid_activities")

    hits = await search_places(db_session, "Gembira")
    assert [hit.kind for hit in hits] == ["transit"]

    bbox = BBox(min_lon=110.39, min_lat=-7.81, max_lon=110.41, max_lat=-7.79)
    assert await query_features_in_viewport(db_session, "poi", bbox) == []
    assert len(await query_features_in_viewport(db_session, "transit", bbox)) == 1


async def test_an_ordinary_poi_still_shows(db_session):
    """The exclusion is keyed on the row being filed elsewhere, not on being a
    mission row — a warung must not vanish with it."""
    await upsert_poi(
        db_session,
        [
            Feature(
                external_id="p9",
                properties={"nama_tempat": "Warung Bu Tini"},
                geometry={"type": "Point", "coordinates": [110.37, -7.80]},
            )
        ],
        "menugo",
    )

    hits = await search_places(db_session, "Warung")
    assert [hit.kind for hit in hits] == ["poi"]


class _CappedActivityFeed:
    """The live `activities` endpoint, as measured.

    Filters by polygon, sorts newest first, answers at most `cap` posts, and
    reports neither a total nor a `hasMore` — so a truncated answer looks
    exactly like a complete one. `offset` is accepted and ignored, which is
    what makes paging useless and tiling necessary.
    """

    def __init__(self, features: list[Feature], cap: int = ACTIVITIES_RESPONSE_CAP) -> None:
        self._features = features
        self._cap = cap
        self.requests = 0

    async def fetch_missions(self, dataset, polygon, *, limit=100, offset=0, **_):
        self.requests += 1
        if dataset != "activities":
            return MissionPage(features=[], has_more=False)
        inside = [
            feature
            for feature in self._features
            if polygon.covers(Point(*feature.geometry["coordinates"]))
        ]
        inside.sort(key=lambda f: f.properties["created_at"], reverse=True)
        return MissionPage(features=inside[: self._cap], has_more=False)

    @staticmethod
    def basemap_style_url(style: str, key: str) -> str:
        return ""


def _grid_of_activities(n: int) -> list[Feature]:
    """`n` posts spread over the study square, oldest last."""
    side = ceil(sqrt(n))
    features = []
    for i in range(n):
        lon = 110.21 + (i % side) * (0.28 / side)
        lat = -7.89 + (i // side) * (0.18 / side)
        features.append(
            Feature(
                external_id=f"act-{i:04d}",
                properties={"title": f"Halte {i}", "created_at": f"2026-08-{(i % 28) + 1:02d}"},
                geometry={"type": "Point", "coordinates": [lon, lat]},
            )
        )
    return features


async def test_tiling_recovers_every_activity_the_cap_would_have_hidden():
    posts = _grid_of_activities(240)
    feed = _CappedActivityFeed(posts)

    # One flat request is what the endpoint gives you: the newest 60, silently.
    flat = await feed.fetch_missions("activities", _POLYGON)
    assert len(flat.features) == ACTIVITIES_RESPONSE_CAP
    assert flat.has_more is False

    harvest = await fetch_activities_in_full(feed, _POLYGON)
    assert {f.external_id for f in harvest.features} == {f.external_id for f in posts}
    assert harvest.capped_tiles == 0


async def test_tiling_stops_at_max_depth_and_says_so():
    """240 posts at one coordinate cannot be split apart — say so, don't spin."""
    stacked = [
        Feature(
            external_id=f"same-{i}",
            properties={"title": "Halte", "created_at": "2026-08-01"},
            geometry={"type": "Point", "coordinates": [110.37, -7.80]},
        )
        for i in range(240)
    ]
    harvest = await fetch_activities_in_full(_CappedActivityFeed(stacked), _POLYGON, max_depth=2)

    assert harvest.capped_tiles > 0
    assert len(harvest.features) == ACTIVITIES_RESPONSE_CAP


async def test_a_feed_under_the_cap_is_taken_in_one_request():
    feed = _CappedActivityFeed(_grid_of_activities(12))
    harvest = await fetch_activities_in_full(feed, _POLYGON)

    assert len(harvest.features) == 12
    assert feed.requests == 1


async def test_survey_etl_files_what_tiling_recovered(db_session):
    feed = _CappedActivityFeed(_grid_of_activities(150))
    counts = await run_activity_survey_etl(feed, db_session, _POLYGON)

    # Every post here is titled "Halte N", and all 150 must land — not the 60
    # a single request would have returned.
    assert counts["halte"] == 150
    assert counts["capped_tiles"] == 0
