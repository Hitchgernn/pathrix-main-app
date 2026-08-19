from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200_with_expected_shape():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] in ("ok", "degraded", "down")
    assert body["redis"] in ("ok", "degraded", "down")
    assert body["graph_loaded"] is False


def test_health_degrades_when_db_and_redis_are_unreachable():
    with TestClient(app) as client:
        with (
            patch("app.api.routes._check_db", new=AsyncMock(return_value="down")),
            patch("app.api.routes._check_redis", new=AsyncMock(return_value="down")),
        ):
            response = client.get("/api/health")
    body = response.json()
    assert body["db"] == "down"
    assert body["redis"] == "down"
