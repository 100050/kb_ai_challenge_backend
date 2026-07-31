from app.services.calculation_explanations import (
    calculation_breakdown,
    calculation_formula,
)


def test_calculation_formula_explains_monthly_loan_interest() -> None:
    result = calculation_formula("monthly_deposit_loan_interest")

    assert result["label"] == "보증금대출 월 이자"
    assert result["formula"] == "보증금대출액 × 연이자율 ÷ 100 ÷ 12"
    assert result["rounding"] == "원 단위 반올림(ROUND_HALF_UP)"


def test_calculation_breakdown_uses_stored_inputs_and_result() -> None:
    context = {
        "analysis": {
            "cash_flow": {
                "after_tax_monthly_income": 3_000_000,
                "monthly_living_expenses_excluding_housing_and_transport": (
                    1_000_000
                ),
                "existing_loan_monthly_payment": 200_000,
            },
            "financial_goals": {
                "target_monthly_savings": 500_000,
                "monthly_safety_margin": 100_000,
            },
            "housing_plans": [
                {
                    "property_id": "property-1",
                    "name": "테스트 매물",
                    "monthly_rent": 700_000,
                },
            ],
        },
        "evaluation": {
            "candidates": [
                {
                    "property_id": "property-1",
                    "monthly_cash_flow": {
                        "actual_monthly_balance": 400_000,
                    },
                    "calculation_details": {
                        "base_monthly_balance": 900_000,
                    },
                },
            ],
        },
    }

    result = calculation_breakdown(
        context,
        "property-1",
        "actual_monthly_balance",
    )

    assert result["status"] == "available"
    assert result["operands"] == {
        "기본 월 잔여금": 900_000,
        "목표 월 저축액": 500_000,
    }
    assert result["result"] == 400_000
