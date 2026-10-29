from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_endpoint_reports_ok() -> None:
    for path in ("/health", "/api/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_unknown_routes_are_not_successful() -> None:
    response = client.get("/schemes")

    assert response.status_code == 404
