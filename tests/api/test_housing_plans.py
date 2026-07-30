from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.main import app


class FakeHousingPlanService:
    def __init__(self) -> None:
        self.analysis_id = uuid4()
        self.records: dict[UUID, dict] = {}

    async def create_housing_plan(
        self,
        analysis_id: UUID,
        payload: object,
    ) -> dict | None:
        if analysis_id != self.analysis_id:
            return None
        now = datetime.now(timezone.utc)
        property_id = uuid4()
        record = {
            "analysis_id": analysis_id,
            "property_id": property_id,
            "name": None,
            "address": None,
            "housing_type": None,
            "deposit": None,
            "monthly_rent": None,
            "maintenance_fee": None,
            "utilities": None,
            "transportation_cost": None,
            "loan_plan": None,
            "additional_costs": None,
            "is_complete": False,
            "created_at": now,
            "updated_at": now,
        }
        record.update(payload.model_dump(exclude_unset=True))
        self.records[property_id] = record
        return record

    async def list_housing_plans(self, analysis_id: UUID) -> list[dict] | None:
        if analysis_id != self.analysis_id:
            return None
        return list(self.records.values())

    async def get_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
    ) -> dict | None:
        if analysis_id != self.analysis_id:
            return None
        return self.records.get(property_id)

    async def update_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
        payload: object,
    ) -> dict | None:
        record = await self.get_housing_plan(analysis_id, property_id)
        if record is None:
            return None
        record.update(payload.model_dump(exclude_unset=True))
        required = (
            "name",
            "address",
            "housing_type",
            "deposit",
            "monthly_rent",
            "maintenance_fee",
            "utilities",
            "transportation_cost",
            "loan_plan",
            "additional_costs",
        )
        record["is_complete"] = all(record[field] is not None for field in required)
        record["updated_at"] = datetime.now(timezone.utc)
        return record

    async def delete_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
    ) -> bool:
        if analysis_id != self.analysis_id:
            return False
        return self.records.pop(property_id, None) is not None


def test_housing_plan_crud_and_partial_save() -> None:
    service = FakeHousingPlanService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            created = client.post(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans",
                json={"name": "역삼 원룸"},
            )
            property_id = created.json()["property_id"]
            updated = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans/{property_id}",
                json={
                    "address": "서울특별시 강남구 역삼동",
                    "housing_type": "monthly_rent",
                    "deposit": 10_000_000,
                    "monthly_rent": 700_000,
                    "maintenance_fee": 100_000,
                    "utilities": 50_000,
                    "transportation_cost": 80_000,
                    "loan_plan": {
                        "deposit_loan_amount": 0,
                        "annual_interest_rate": 0,
                    },
                    "additional_costs": {
                        "brokerage_fee": 300_000,
                        "moving_cost": 1_000_000,
                        "other_move_in_cost": 300_000,
                    },
                },
            )
            listed = client.get(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans",
            )
            fetched = client.get(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans/{property_id}",
            )
            deleted = client.delete(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans/{property_id}",
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["name"] == "역삼 원룸"
    assert created.json()["is_complete"] is False
    assert updated.status_code == 200
    assert updated.json()["name"] == "역삼 원룸"
    assert updated.json()["is_complete"] is True
    assert listed.status_code == 200
    assert len(listed.json()["housing_plans"]) == 1
    assert fetched.status_code == 200
    assert fetched.json()["property_id"] == property_id
    assert deleted.status_code == 204


def test_housing_plan_must_belong_to_analysis() -> None:
    service = FakeHousingPlanService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans/{uuid4()}",
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HOUSING_PLAN_NOT_FOUND"


def test_housing_plan_rejects_purchase_type() -> None:
    service = FakeHousingPlanService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans",
                json={"housing_type": "purchase"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_housing_plan_rejects_client_supplied_legal_dong_code() -> None:
    service = FakeHousingPlanService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/analyses/{service.analysis_id}/housing-plans",
                json={"legal_dong_code": "1168010100"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
