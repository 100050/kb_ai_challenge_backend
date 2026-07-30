from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CommonFinancialInput(BaseModel):
    after_tax_monthly_income: int
    monthly_living_expenses_excluding_housing_and_transport: int
    existing_loan_monthly_payment: int
    target_monthly_savings: int
    monthly_safety_margin: int
    available_cash: int
    minimum_emergency_fund: int
    recoverable_existing_rental_deposit: int


class PropertyFinancialInput(BaseModel):
    property_id: UUID
    name: str
    deposit: int
    monthly_rent: int
    maintenance_fee: int
    utilities: int
    transportation_cost: int
    deposit_loan_amount: int
    annual_interest_rate: Decimal
    brokerage_fee: int
    moving_cost: int
    other_move_in_cost: int


class InitialFundsResult(BaseModel):
    initial_cash_required: int
    post_move_liquid_assets: int
    emergency_fund_gap: int
    status: Literal[
        "insufficient_initial_funds",
        "emergency_fund_shortfall",
        "sufficient",
    ]


class MonthlyCashFlowResult(BaseModel):
    monthly_housing_and_transport_cost: int
    actual_monthly_balance: int
    monthly_budget_margin: int
    status: Literal[
        "essential_expense_deficit",
        "savings_target_shortfall",
        "safety_margin_shortfall",
        "sufficient",
    ]


class AnnualGoalResult(BaseModel):
    annual_financial_target: int
    expected_resources_after_one_year: int
    annual_financial_surplus: int
    annual_goal_achievement_rate: float
    status: Literal["below_target", "target_met", "above_target"]


class CalculationDetails(BaseModel):
    available_own_funds: int
    self_funded_deposit: int
    monthly_deposit_loan_interest: int
    monthly_housing_cash_outflow: int
    base_monthly_balance: int


class EvaluationWarning(BaseModel):
    code: str
    message: str


class PriceComparableSample(BaseModel):
    deposit: int
    monthly_rent: int
    exclusive_area_m2: float
    contract_date: date
    equivalent_monthly_cost: int


class PriceAppropriatenessResult(BaseModel):
    status: Literal["available", "unavailable"]
    sample_count: int = 0
    comparison_mode: Literal["median", "individual_samples"] | None = None
    median_equivalent_monthly_cost: int | None = None
    difference_from_median: int | None = None
    difference_rate_from_median: float | None = None
    price_percentile: float | None = None
    samples: list[PriceComparableSample] = Field(default_factory=list)
    reason: str | None = None


class PropertyFinancialEvaluation(BaseModel):
    property_id: UUID
    name: str
    initial_funds: InitialFundsResult
    monthly_cash_flow: MonthlyCashFlowResult
    annual_goal: AnnualGoalResult
    price_appropriateness: PriceAppropriatenessResult | None = None
    calculation_details: CalculationDetails
    warnings: list[EvaluationWarning]


class FinancialEvaluationResult(BaseModel):
    analysis_id: UUID
    candidates: list[PropertyFinancialEvaluation]
    generated_at: datetime


class EvaluationStarted(BaseModel):
    evaluation_id: UUID
    status: Literal["completed"]
    progress: Literal[100]


class EvaluationStatus(BaseModel):
    evaluation_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    current_stage: str | None
    progress: int
    error: str | None
    updated_at: datetime
