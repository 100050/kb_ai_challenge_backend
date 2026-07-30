from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Money = Annotated[int, Field(ge=0)]
InterestRate = Annotated[float, Field(ge=0)]
Area = Annotated[float, Field(gt=0)]
PropertyType = Literal[
    "apartment",
    "row_house",
    "multi_family",
    "officetel",
    "detached_house",
    "multi_household",
]


class LoanPlan(BaseModel):
    deposit_loan_amount: Money
    annual_interest_rate: InterestRate


class AdditionalCosts(BaseModel):
    brokerage_fee: Money
    moving_cost: Money
    other_move_in_cost: Money


class HousingPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    property_type: PropertyType | None = None
    exclusive_area_m2: Area | None = None
    housing_type: Literal["jeonse", "monthly_rent"] | None = None
    deposit: Money | None = None
    monthly_rent: Money | None = None
    maintenance_fee: Money | None = None
    utilities: Money | None = None
    transportation_cost: Money | None = None
    loan_plan: LoanPlan | None = None
    additional_costs: AdditionalCosts | None = None


class HousingPlanCreate(HousingPlanUpdate):
    pass


class HousingPlanResponse(BaseModel):
    analysis_id: UUID
    property_id: UUID
    name: str | None
    address: str | None
    property_type: PropertyType | None = None
    legal_dong_code: str | None = None
    exclusive_area_m2: float | None = None
    housing_type: Literal["jeonse", "monthly_rent"] | None
    deposit: int | None
    monthly_rent: int | None
    maintenance_fee: int | None
    utilities: int | None
    transportation_cost: int | None
    loan_plan: LoanPlan | None
    additional_costs: AdditionalCosts | None
    is_complete: bool
    created_at: datetime
    updated_at: datetime


class HousingPlanSummary(BaseModel):
    property_id: UUID
    name: str | None
    housing_type: Literal["jeonse", "monthly_rent"] | None
    is_complete: bool
    updated_at: datetime


class HousingPlanListResponse(BaseModel):
    housing_plans: list[HousingPlanSummary]
