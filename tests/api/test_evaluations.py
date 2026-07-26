from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_evaluation_service
from app.main import app


class FakeEvaluationService:
    def __init__(self) -> None:
        self.analysis_id = uuid4()
        self.evaluation_id = uuid4()

    async def evaluate(self, analysis_id: UUID) -> dict | None:
        if analysis_id != self.analysis_id:
            return None
        return {
            "evaluation_id": self.evaluation_id,
            "status": "completed",
            "progress": 100,
        }

    async def get_status(self, analysis_id: UUID) -> dict | None:
        if analysis_id != self.analysis_id:
            return None
        return {
            "evaluation_id": self.evaluation_id,
            "status": "completed",
            "current_stage": "financial_management",
            "progress": 100,
            "error": None,
            "updated_at": datetime.now(timezone.utc),
        }

    async def get_result(self, analysis_id: UUID) -> dict | None:
        if analysis_id != self.analysis_id:
            return None
        return {
            "analysis_id": self.analysis_id,
            "candidates": [],
            "generated_at": datetime.now(timezone.utc),
        }


def test_evaluation_execute_status_result_and_sse() -> None:
    service = FakeEvaluationService()
    app.dependency_overrides[get_evaluation_service] = lambda: service

    try:
        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/analyses/{service.analysis_id}/evaluation",
            )
            status_response = client.get(
                f"/api/v1/analyses/{service.analysis_id}/evaluation",
            )
            result = client.get(
                f"/api/v1/analyses/{service.analysis_id}/result",
            )
            events = client.get(
                f"/api/v1/analyses/{service.analysis_id}/evaluation/events",
            )
    finally:
        app.dependency_overrides.clear()

    assert started.status_code == 202
    assert started.json()["status"] == "completed"
    assert status_response.status_code == 200
    assert status_response.json()["current_stage"] == "financial_management"
    assert result.status_code == 200
    assert result.json()["analysis_id"] == str(service.analysis_id)
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: completed" in events.text


def test_missing_evaluation_returns_common_error() -> None:
    service = FakeEvaluationService()
    app.dependency_overrides[get_evaluation_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/analyses/{uuid4()}/evaluation")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EVALUATION_NOT_FOUND"
