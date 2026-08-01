from decimal import Decimal
from uuid import uuid4

from app.schemas.evaluation import (
    CommonFinancialInput,
    PropertyFinancialInput,
)
from app.services.financial_calculations import evaluate_property


def common_input() -> CommonFinancialInput:
    return CommonFinancialInput(
        after_tax_monthly_income=3_500_000,
        monthly_living_expenses_excluding_housing_and_transport=1_300_000,
        existing_loan_monthly_payment=200_000,
        target_monthly_savings=700_000,
        monthly_safety_margin=300_000,
        available_cash=75_000_000,
        minimum_emergency_fund=10_000_000,
        recoverable_existing_rental_deposit=20_000_000,
        existing_rental_deposit_available_before_contract=True,
    )


def property_input() -> PropertyFinancialInput:
    return PropertyFinancialInput(
        property_id=uuid4(),
        name="역삼 원룸",
        memo="역세권, 엘리베이터 있음",
        deposit=10_000_000,
        monthly_rent=700_000,
        maintenance_fee=100_000,
        utilities=50_000,
        transportation_cost=80_000,
        deposit_loan_amount=0,
        annual_interest_rate=Decimal("0"),
        brokerage_fee=300_000,
        moving_cost=1_000_000,
        other_move_in_cost=300_000,
    )


def test_evaluate_property_calculates_three_financial_cards() -> None:
    result = evaluate_property(common_input(), property_input())

    assert result.memo == "역세권, 엘리베이터 있음"
    assert result.initial_funds.available_cash == 75_000_000
    assert result.initial_funds.available_own_funds == 95_000_000
    assert (
        result.initial_funds.contract_available_total_funds
        == 95_000_000
    )
    assert result.initial_funds.initial_cash_required == 11_600_000
    assert result.initial_funds.minimum_emergency_fund == 10_000_000
    assert result.initial_funds.post_move_liquid_assets == 83_400_000
    assert result.initial_funds.emergency_fund_gap == 73_400_000
    assert result.initial_funds.status == "sufficient"

    assert result.monthly_cash_flow.monthly_housing_and_transport_cost == 930_000
    assert result.monthly_cash_flow.monthly_income == 3_500_000
    assert result.monthly_cash_flow.essential_monthly_outflow == 2_430_000
    assert result.monthly_cash_flow.base_monthly_balance == 1_070_000
    assert result.monthly_cash_flow.target_monthly_savings == 700_000
    assert result.monthly_cash_flow.actual_monthly_balance == 370_000
    assert result.monthly_cash_flow.monthly_budget_margin == 70_000
    assert result.monthly_cash_flow.status == "sufficient"

    assert result.annual_goal.annual_financial_target == 18_400_000
    assert result.annual_goal.expected_resources_after_one_year == 96_240_000
    assert result.annual_goal.annual_financial_surplus == 77_840_000
    assert result.annual_goal.annual_goal_achievement_rate == 523.04
    assert result.annual_goal.status == "above_target"
    assert result.overall_financial_status == "all_satisfied"


def test_monthly_interest_is_rounded_half_up_to_won() -> None:
    housing = property_input().model_copy(
        update={
            "deposit_loan_amount": 100_000_000,
            "annual_interest_rate": Decimal("3.5"),
        },
    )

    result = evaluate_property(common_input(), housing)

    assert result.calculation_details.monthly_deposit_loan_interest == 291_667


def test_deferred_existing_deposit_is_excluded_initially_but_added_in_one_year(
) -> None:
    immediate = evaluate_property(common_input(), property_input())
    deferred_common = common_input().model_copy(
        update={
            "existing_rental_deposit_available_before_contract": False,
        },
    )

    deferred = evaluate_property(deferred_common, property_input())

    assert deferred.initial_funds.post_move_liquid_assets == 63_400_000
    assert (
        deferred.calculation_details.initially_available_existing_deposit
        == 0
    )
    assert deferred.calculation_details.deferred_existing_deposit == 20_000_000
    assert (
        deferred.annual_goal.expected_resources_after_one_year
        == immediate.annual_goal.expected_resources_after_one_year
        == 96_240_000
    )


def test_status_priority_starts_with_initial_funds_and_essential_cash_flow() -> None:
    common = common_input().model_copy(
        update={
            "available_cash": 0,
            "recoverable_existing_rental_deposit": 0,
        },
    )
    housing = property_input().model_copy(update={"monthly_rent": 4_000_000})

    result = evaluate_property(common, housing)

    assert result.initial_funds.status == "insufficient_initial_funds"
    assert result.monthly_cash_flow.status == "essential_expense_deficit"
    assert result.warnings[0].code == "INSUFFICIENT_INITIAL_FUNDS"


def test_zero_annual_target_does_not_calculate_achievement_rate() -> None:
    common = common_input().model_copy(
        update={
            "minimum_emergency_fund": 0,
            "target_monthly_savings": 0,
        },
    )

    result = evaluate_property(common, property_input())

    assert result.annual_goal.annual_financial_target == 0
    assert result.annual_goal.annual_goal_achievement_rate is None
