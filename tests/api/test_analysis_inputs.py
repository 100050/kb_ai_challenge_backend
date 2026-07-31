from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.main import app


class FakeInputService:
    def __init__(self) -> None:
        self.analysis_id = uuid4()
        self.cash_flow: dict[str, int | None] = {
            "after_tax_monthly_income": None,
            "monthly_living_expenses_excluding_housing_and_transport": None,
            "existing_loan_monthly_payment": None,
        }
        self.financial_goals: dict[str, int | bool | None] = {
            "target_monthly_savings": None,
            "monthly_safety_margin": None,
            "available_cash": None,
            "minimum_emergency_fund": None,
            "recoverable_existing_rental_deposit": None,
            "existing_rental_deposit_available_before_contract": None,
        }

    async def update_cash_flow(self, analysis_id: UUID, payload: object) -> dict:
        if analysis_id != self.analysis_id:
            return None
        self.cash_flow.update(payload.model_dump(exclude_unset=True))
        is_complete = all(value is not None for value in self.cash_flow.values())
        return {
            "analysis_id": analysis_id,
            "cash_flow": self.cash_flow,
            "current_step": "financial_goals" if is_complete else "cash_flow",
            "progress": 33 if is_complete else 0,
        }

    async def update_financial_goals(
        self,
        analysis_id: UUID,
        payload: object,
    ) -> dict:
        if analysis_id != self.analysis_id:
            return None
        self.financial_goals.update(payload.model_dump(exclude_unset=True))
        is_complete = all(
            value is not None for value in self.financial_goals.values()
        )
        return {
            "analysis_id": analysis_id,
            "financial_goals": self.financial_goals,
            "current_step": "housing_plan" if is_complete else "financial_goals",
            "progress": 67 if is_complete else 33,
        }


def test_cash_flow_patch_updates_only_provided_fields() -> None:
    service = FakeInputService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            first = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/cash-flow",
                json={"after_tax_monthly_income": 3_500_000},
            )
            second = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/cash-flow",
                json={
                    "monthly_living_expenses_excluding_housing_and_transport": 1_300_000,
                    "existing_loan_monthly_payment": 200_000,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["cash_flow"]["existing_loan_monthly_payment"] is None
    assert first.json()["current_step"] == "cash_flow"
    assert second.status_code == 200
    assert second.json()["cash_flow"]["after_tax_monthly_income"] == 3_500_000
    assert second.json()["current_step"] == "financial_goals"
    assert second.json()["progress"] == 33


def test_financial_goals_patch_updates_only_provided_fields() -> None:
    service = FakeInputService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            first = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/financial-goals",
                json={
                    "target_monthly_savings": 700_000,
                    "available_cash": 75_000_000,
                },
            )
            second = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/financial-goals",
                json={
                    "monthly_safety_margin": 300_000,
                    "minimum_emergency_fund": 10_000_000,
                    "recoverable_existing_rental_deposit": 20_000_000,
                    "existing_rental_deposit_available_before_contract": False,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["financial_goals"]["monthly_safety_margin"] is None
    assert second.status_code == 200
    assert second.json()["financial_goals"]["target_monthly_savings"] == 700_000
    assert (
        second.json()["financial_goals"]
        ["existing_rental_deposit_available_before_contract"]
        is False
    )
    assert second.json()["current_step"] == "housing_plan"
    assert second.json()["progress"] == 67


def test_input_patch_rejects_negative_money() -> None:
    service = FakeInputService()
    app.dependency_overrides[get_analysis_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/analyses/{service.analysis_id}/cash-flow",
                json={"after_tax_monthly_income": -1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
