from app.models.analysis import Analysis
from app.models.housing_plan import HousingPlan
from app.schemas.housing_plan import HousingPlanUpdate
from app.services.analysis import AnalysisService


def complete_housing_plan() -> HousingPlan:
    return HousingPlan(
        name="역삼 원룸",
        address="서울특별시 강남구 역삼동",
        housing_type="monthly_rent",
        deposit=10_000_000,
        monthly_rent=700_000,
        maintenance_fee=100_000,
        utilities=50_000,
        transportation_cost=80_000,
        deposit_loan_amount=0,
        annual_interest_rate=0,
        brokerage_fee=300_000,
        moving_cost=1_000_000,
        other_move_in_cost=300_000,
    )


def test_progress_follows_the_first_incomplete_step() -> None:
    analysis = Analysis()

    AnalysisService._update_progress(analysis, [])
    assert (analysis.current_step, analysis.progress) == ("cash_flow", 0)

    analysis.after_tax_monthly_income = 3_500_000
    analysis.monthly_living_expenses_excluding_housing_and_transport = 1_300_000
    analysis.existing_loan_monthly_payment = 200_000
    AnalysisService._update_progress(analysis, [])
    assert (analysis.current_step, analysis.progress) == (
        "financial_goals",
        33,
    )

    analysis.target_monthly_savings = 700_000
    analysis.monthly_safety_margin = 300_000
    analysis.available_cash = 75_000_000
    analysis.minimum_emergency_fund = 10_000_000
    analysis.recoverable_existing_rental_deposit = 20_000_000
    analysis.existing_rental_deposit_available_before_contract = True
    AnalysisService._update_progress(analysis, [])
    assert (analysis.current_step, analysis.progress) == ("housing_plan", 67)

    AnalysisService._update_progress(analysis, [complete_housing_plan()])
    assert (analysis.current_step, analysis.progress) == ("confirmation", 100)


def test_housing_plan_accepts_zero_as_a_completed_cost() -> None:
    housing_plan = complete_housing_plan()

    assert housing_plan.is_complete is True


def test_explicit_null_clears_nested_housing_plan_values() -> None:
    housing_plan = complete_housing_plan()

    AnalysisService._apply_housing_plan_update(
        housing_plan,
        HousingPlanUpdate(
            loan_plan=None,
            additional_costs=None,
        ),
    )

    assert housing_plan.deposit_loan_amount is None
    assert housing_plan.annual_interest_rate is None
    assert housing_plan.brokerage_fee is None
    assert housing_plan.moving_cost is None
    assert housing_plan.other_move_in_cost is None


def test_same_housing_plan_patch_is_not_treated_as_a_change() -> None:
    housing_plan = complete_housing_plan()
    previous_updated_at = housing_plan.updated_at

    changed = AnalysisService._apply_housing_plan_update(
        housing_plan,
        HousingPlanUpdate(monthly_rent=700_000),
    )

    assert changed is False
    assert housing_plan.updated_at == previous_updated_at
