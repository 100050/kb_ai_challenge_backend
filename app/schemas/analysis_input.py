from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


Money = Annotated[int, Field(ge=0)]


class CashFlowUpdate(BaseModel):
    after_tax_monthly_income: Money | None = None
    monthly_living_expenses_excluding_housing_and_transport: Money | None = None
    existing_loan_monthly_payment: Money | None = None


class CashFlow(BaseModel):
    after_tax_monthly_income: int | None
    monthly_living_expenses_excluding_housing_and_transport: int | None
    existing_loan_monthly_payment: int | None


class CashFlowResponse(BaseModel):
    analysis_id: UUID
    cash_flow: CashFlow
    current_step: str
    progress: int


class FinancialGoalsUpdate(BaseModel):
    target_monthly_savings: Money | None = None
    monthly_safety_margin: Money | None = None
    available_cash: Money | None = None
    minimum_emergency_fund: Money | None = None
    recoverable_existing_rental_deposit: Money | None = None


class FinancialGoals(BaseModel):
    target_monthly_savings: int | None
    monthly_safety_margin: int | None
    available_cash: int | None
    minimum_emergency_fund: int | None
    recoverable_existing_rental_deposit: int | None


class FinancialGoalsResponse(BaseModel):
    analysis_id: UUID
    financial_goals: FinancialGoals
    current_step: str
    progress: int
