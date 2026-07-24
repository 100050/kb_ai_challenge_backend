from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.main import app
from app.schemas.analysis import AnalysisDetail, AnalysisSummary


class FakeAnalysisService:
    def __init__(self) -> None:
        self.records: dict[UUID, AnalysisDetail] = {}

    async def create(self) -> AnalysisSummary:
        now = datetime.now(timezone.utc)
        analysis = AnalysisDetail(
            analysis_id=uuid4(),
            status="draft",
            current_step="properties",
            progress=0,
            properties=None,
            cash_flow=None,
            financial_goals=None,
            loan_plan=None,
            created_at=now,
            updated_at=now,
        )
        self.records[analysis.analysis_id] = analysis
        return AnalysisSummary.model_validate(analysis)

    async def get(self, analysis_id: UUID) -> AnalysisDetail | None:
        return self.records.get(analysis_id)

    async def delete(self, analysis_id: UUID) -> bool:
        return self.records.pop(analysis_id, None) is not None


def test_create_analysis() -> None:
    service = FakeAnalysisService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/analyses")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["analysis_id"])
    assert body["status"] == "draft"
    assert body["current_step"] == "properties"
    assert body["progress"] == 0
    assert body["created_at"].endswith("Z")


def test_get_analysis() -> None:
    service = FakeAnalysisService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/analyses").json()
            response = client.get(
                f"/api/v1/analyses/{created['analysis_id']}",
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == created["analysis_id"]
    assert body["properties"] is None
    assert body["cash_flow"] is None
    assert body["financial_goals"] is None
    assert body["loan_plan"] is None
    assert body["updated_at"].endswith("Z")


def test_get_missing_analysis_returns_common_error() -> None:
    service = FakeAnalysisService()
    app.dependency_overrides[get_analysis_service] = lambda: service
    missing_id = uuid4()

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/analyses/{missing_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "ANALYSIS_NOT_FOUND",
            "message": "분석을 찾을 수 없습니다.",
            "details": [],
        }
    }


def test_delete_analysis() -> None:
    service = FakeAnalysisService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/analyses").json()
            response = client.delete(
                f"/api/v1/analyses/{created['analysis_id']}",
            )
            get_response = client.get(
                f"/api/v1/analyses/{created['analysis_id']}",
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    assert get_response.status_code == 404


def test_delete_missing_analysis_returns_common_error() -> None:
    service = FakeAnalysisService()
    app.dependency_overrides[get_analysis_service] = lambda: service
    missing_id = uuid4()

    try:
        with TestClient(app) as client:
            response = client.delete(f"/api/v1/analyses/{missing_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_invalid_analysis_id_returns_common_validation_error() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/analyses/not-a-uuid")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "입력값을 확인해 주세요."
    assert body["error"]["details"][0]["field"] == "analysis_id"
