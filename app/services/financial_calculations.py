from decimal import Decimal, ROUND_HALF_UP

from app.schemas.evaluation import (
    AnnualGoalResult,
    CalculationDetails,
    CommonFinancialInput,
    EvaluationWarning,
    InitialFundsResult,
    MonthlyCashFlowResult,
    PropertyFinancialEvaluation,
    PropertyFinancialInput,
)


WON = Decimal("1")
PERCENT = Decimal("100")
MONTHS_PER_YEAR = Decimal("12")


def round_won(value: Decimal) -> int:
    return int(value.quantize(WON, rounding=ROUND_HALF_UP))


def evaluate_property(
    common: CommonFinancialInput,
    housing: PropertyFinancialInput,
) -> PropertyFinancialEvaluation:
    available_own_funds = (
        common.available_cash
        + common.recoverable_existing_rental_deposit
    )
    self_funded_deposit = (
        housing.deposit - housing.deposit_loan_amount
    )
    initial_cash_required = (
        self_funded_deposit
        + housing.brokerage_fee
        + housing.moving_cost
        + housing.other_move_in_cost
    )
    post_move_liquid_assets = (
        available_own_funds - initial_cash_required
    )
    emergency_fund_gap = (
        post_move_liquid_assets - common.minimum_emergency_fund
    )

    if post_move_liquid_assets < 0:
        initial_status = "insufficient_initial_funds"
    elif emergency_fund_gap < 0:
        initial_status = "emergency_fund_shortfall"
    else:
        initial_status = "sufficient"

    monthly_deposit_loan_interest = round_won(
        Decimal(housing.deposit_loan_amount)
        * housing.annual_interest_rate
        / PERCENT
        / MONTHS_PER_YEAR,
    )
    monthly_housing_cash_outflow = (
        housing.monthly_rent
        + housing.maintenance_fee
        + housing.utilities
        + monthly_deposit_loan_interest
    )
    monthly_housing_and_transport_cost = (
        monthly_housing_cash_outflow
        + housing.transportation_cost
    )
    essential_monthly_outflow = (
        common.monthly_living_expenses_excluding_housing_and_transport
        + common.existing_loan_monthly_payment
        + monthly_housing_and_transport_cost
    )
    base_monthly_balance = (
        common.after_tax_monthly_income - essential_monthly_outflow
    )
    actual_monthly_balance = (
        base_monthly_balance - common.target_monthly_savings
    )
    monthly_budget_margin = (
        actual_monthly_balance - common.monthly_safety_margin
    )

    if base_monthly_balance < 0:
        monthly_status = "essential_expense_deficit"
    elif actual_monthly_balance < 0:
        monthly_status = "savings_target_shortfall"
    elif monthly_budget_margin < 0:
        monthly_status = "safety_margin_shortfall"
    else:
        monthly_status = "sufficient"

    annual_financial_target = (
        common.minimum_emergency_fund
        + 12 * common.target_monthly_savings
    )
    expected_resources_after_one_year = (
        post_move_liquid_assets
        + 12
        * (
            common.target_monthly_savings
            + actual_monthly_balance
        )
    )
    annual_financial_surplus = (
        expected_resources_after_one_year
        - annual_financial_target
    )
    if annual_financial_target == 0:
        achievement_rate = (
            Decimal("100.00")
            if expected_resources_after_one_year >= 0
            else Decimal("0.00")
        )
    else:
        achievement_rate = (
            Decimal(expected_resources_after_one_year)
            / Decimal(annual_financial_target)
            * PERCENT
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if annual_financial_surplus < 0:
        annual_status = "below_target"
    elif annual_financial_surplus == 0:
        annual_status = "target_met"
    else:
        annual_status = "above_target"

    warnings: list[EvaluationWarning] = []
    if post_move_liquid_assets < 0:
        warnings.append(
            EvaluationWarning(
                code="INSUFFICIENT_INITIAL_FUNDS",
                message=(
                    "초기자금이 부족하여 이후 계산은 계약 체결을 "
                    "가정한 참고값입니다."
                ),
            ),
        )

    return PropertyFinancialEvaluation(
        property_id=housing.property_id,
        name=housing.name,
        memo=housing.memo,
        initial_funds=InitialFundsResult(
            initial_cash_required=initial_cash_required,
            post_move_liquid_assets=post_move_liquid_assets,
            emergency_fund_gap=emergency_fund_gap,
            status=initial_status,
        ),
        monthly_cash_flow=MonthlyCashFlowResult(
            monthly_housing_and_transport_cost=(
                monthly_housing_and_transport_cost
            ),
            actual_monthly_balance=actual_monthly_balance,
            monthly_budget_margin=monthly_budget_margin,
            status=monthly_status,
        ),
        annual_goal=AnnualGoalResult(
            annual_financial_target=annual_financial_target,
            expected_resources_after_one_year=(
                expected_resources_after_one_year
            ),
            annual_financial_surplus=annual_financial_surplus,
            annual_goal_achievement_rate=float(achievement_rate),
            status=annual_status,
        ),
        calculation_details=CalculationDetails(
            available_own_funds=available_own_funds,
            self_funded_deposit=self_funded_deposit,
            monthly_deposit_loan_interest=(
                monthly_deposit_loan_interest
            ),
            monthly_housing_cash_outflow=monthly_housing_cash_outflow,
            base_monthly_balance=base_monthly_balance,
        ),
        warnings=warnings,
    )
