from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from app.api.dependencies import get_analysis_service
from app.main import app


def test_health_check_is_exposed_under_api_v1() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakeAnalysisService:
    async def create(self) -> dict:
        return {
            "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "draft",
            "current_step": "cash_flow",
            "progress": 0,
            "created_at": datetime.now(timezone.utc),
        }


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
def test_cors_preflight_allows_development_frontend(origin: str) -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/analyses",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
def test_cors_header_is_added_to_post_response(origin: str) -> None:
    app.dependency_overrides[get_analysis_service] = FakeAnalysisService

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyses",
                headers={"Origin": origin},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
