from fastapi.testclient import TestClient
from sqlalchemy import func, insert

from app.data.repository import upsert_poi
from app.data.schema import Isochrone, TransitStop
from app.main import app
from app.models.mapid import Feature


def test_list_layers_returns_the_catalogue():
    with TestClient(app) as client:
        response = client.get("/api/layers")
    assert response.status_code == 200
    ids = {layer["id"] for layer in response.json()}
    assert ids == {"poi", "properti", "transit", "pangkalan"}


def test_layer_features_501_for_an_unqueryable_layer():
    with TestClient(app) as client:
        response = client.get(
            "/api/layers/transit/features",
            params={"min_lon": 110.3, "min_lat": -7.85, "max_lon": 110.4, "max_lat": -7.75},
        )
    assert response.status_code == 501


async def test_layer_features_returns_seeded_poi(db_session):
    feature = Feature(
        external_id="layerfeat1",
        properties={"nama_tempat": "Warung Layer Test"},
        geometry={"type": "Point", "coordinates": [110.37, -7.80]},
    )
    await upsert_poi(db_session, [feature], "menugo")

    with TestClient(app) as client:
        response = client.get(
            "/api/layers/poi/features",
            params={"min_lon": 110.30, "min_lat": -7.85, "max_lon": 110.45, "max_lat": -7.75},
        )
    assert response.status_code == 200
    assert any(f["external_id"] == "layerfeat1" for f in response.json())


def test_isochrone_404_when_not_computed():
    with TestClient(app) as client:
        response = client.get("/api/isochrone/999999", params={"minutes": 15})
    assert response.status_code == 404


async def test_isochrone_returns_geometry_when_present(db_session):
    result = await db_session.execute(
        insert(TransitStop)
        .values(
            external_id="stop1",
            name="Halte Test",
            mode="bus",
            operator="TransJogja",
            geom=func.ST_SetSRID(func.ST_MakePoint(110.37, -7.80), 4326),
            source="test",
        )
        .returning(TransitStop.id)
    )
    stop_id = result.scalar_one()

    envelope_wkt = "POLYGON((110.36 -7.81, 110.38 -7.81, 110.38 -7.79, 110.36 -7.79, 110.36 -7.81))"
    await db_session.execute(
        insert(Isochrone).values(
            stop_id=stop_id,
            minutes=15,
            geom=func.ST_SetSRID(func.ST_GeomFromText(envelope_wkt), 4326),
        )
    )
    await db_session.commit()

    with TestClient(app) as client:
        response = client.get(f"/api/isochrone/{stop_id}", params={"minutes": 15})

    assert response.status_code == 200
    body = response.json()
    assert body["stop_id"] == stop_id
    assert body["minutes"] == 15
    assert body["geometry"]["type"] == "Polygon"
