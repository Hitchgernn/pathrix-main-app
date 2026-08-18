from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200_with_expected_shape():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] in ("ok", "degraded", "down")
    assert body["redis"] in ("ok", "degraded", "down")
    assert body["graph_loaded"] is False


def test_health_degrades_without_db_or_redis_running():
    client = TestClient(app)
    response = client.get("/api/health")
    body = response.json()
    assert body["db"] == "down"
    assert body["redis"] == "down"
