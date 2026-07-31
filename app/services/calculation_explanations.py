from dataclasses import dataclass
from typing import Any, Literal


CalculationMetric = Literal[
    "available_own_funds",
    "self_funded_deposit",
    "initial_cash_required",
    "post_move_liquid_assets",
    "emergency_fund_gap",
    "monthly_deposit_loan_interest",
    "monthly_housing_cash_outflow",
    "monthly_housing_and_transport_cost",
    "essential_monthly_outflow",
    "base_monthly_balance",
    "actual_monthly_balance",
    "monthly_budget_margin",
    "annual_financial_target",
    "expected_resources_after_one_year",
    "annual_financial_surplus",
    "annual_goal_achievement_rate",
    "equivalent_monthly_cost",
    "difference_from_median",
    "difference_rate_from_median",
    "price_percentile",
]


@dataclass(frozen=True)
class FormulaDefinition:
    label: str
    formula: str
    operands: dict[str, str]
    result_path: str
    rounding: str = "원 단위"
    note: str | None = None


FORMULAS: dict[str, FormulaDefinition] = {
    "available_own_funds": FormulaDefinition(
        "가용 자기자금",
        (
            "현재 사용 가능 현금 + 계약일 전에 회수 가능한 "
            "기존 임차보증금"
        ),
        {
            "현재 사용 가능 현금": "analysis.financial_goals.available_cash",
            "계약일 전 가용 기존 임차보증금": (
                "candidate.calculation_details."
                "initially_available_existing_deposit"
            ),
        },
        "candidate.calculation_details.available_own_funds",
        note=(
            "기존 임차보증금을 계약일 전에 회수할 수 없는 경우 "
            "초기자금에는 0원으로 반영합니다."
        ),
    ),
    "self_funded_deposit": FormulaDefinition(
        "자기부담 보증금",
        "보증금 - 보증금대출액",
        {
            "보증금": "housing.deposit",
            "보증금대출액": "housing.loan_plan.deposit_loan_amount",
        },
        "candidate.calculation_details.self_funded_deposit",
    ),
    "initial_cash_required": FormulaDefinition(
        "초기 필요자금",
        "자기부담 보증금 + 중개보수 + 이사비 + 기타 입주비",
        {
            "자기부담 보증금": (
                "candidate.calculation_details.self_funded_deposit"
            ),
            "중개보수": "housing.additional_costs.brokerage_fee",
            "이사비": "housing.additional_costs.moving_cost",
            "기타 입주비": "housing.additional_costs.other_move_in_cost",
        },
        "candidate.initial_funds.initial_cash_required",
    ),
    "post_move_liquid_assets": FormulaDefinition(
        "입주 후 유동자산",
        "가용 자기자금 - 초기 필요자금",
        {
            "가용 자기자금": (
                "candidate.calculation_details.available_own_funds"
            ),
            "초기 필요자금": (
                "candidate.initial_funds.initial_cash_required"
            ),
        },
        "candidate.initial_funds.post_move_liquid_assets",
    ),
    "emergency_fund_gap": FormulaDefinition(
        "최소 비상자금 대비 여유·부족액",
        "입주 후 유동자산 - 최소 비상자금",
        {
            "입주 후 유동자산": (
                "candidate.initial_funds.post_move_liquid_assets"
            ),
            "최소 비상자금": (
                "analysis.financial_goals.minimum_emergency_fund"
            ),
        },
        "candidate.initial_funds.emergency_fund_gap",
    ),
    "monthly_deposit_loan_interest": FormulaDefinition(
        "보증금대출 월 이자",
        "보증금대출액 × 연이자율 ÷ 100 ÷ 12",
        {
            "보증금대출액": "housing.loan_plan.deposit_loan_amount",
            "연이자율(%)": "housing.loan_plan.annual_interest_rate",
        },
        "candidate.calculation_details.monthly_deposit_loan_interest",
        "원 단위 반올림(ROUND_HALF_UP)",
        "대출은 만기일시상환 방식으로 월 이자만 반영합니다.",
    ),
    "monthly_housing_cash_outflow": FormulaDefinition(
        "월 주거 현금유출",
        "월세 + 관리비 + 공과금 + 보증금대출 월 이자",
        {
            "월세": "housing.monthly_rent",
            "관리비": "housing.maintenance_fee",
            "공과금": "housing.utilities",
            "보증금대출 월 이자": (
                "candidate.calculation_details.monthly_deposit_loan_interest"
            ),
        },
        "candidate.calculation_details.monthly_housing_cash_outflow",
    ),
    "monthly_housing_and_transport_cost": FormulaDefinition(
        "월 주거·교통비",
        "월 주거 현금유출 + 교통비",
        {
            "월 주거 현금유출": (
                "candidate.calculation_details.monthly_housing_cash_outflow"
            ),
            "교통비": "housing.transportation_cost",
        },
        "candidate.monthly_cash_flow.monthly_housing_and_transport_cost",
    ),
    "essential_monthly_outflow": FormulaDefinition(
        "필수 월 현금유출",
        "비주거·교통 생활비 + 기존대출 월 상환액 + 월 주거·교통비",
        {
            "비주거·교통 생활비": (
                "analysis.cash_flow."
                "monthly_living_expenses_excluding_housing_and_transport"
            ),
            "기존대출 월 상환액": (
                "analysis.cash_flow.existing_loan_monthly_payment"
            ),
            "월 주거·교통비": (
                "candidate.monthly_cash_flow."
                "monthly_housing_and_transport_cost"
            ),
        },
        "candidate.monthly_cash_flow.essential_monthly_outflow",
    ),
    "base_monthly_balance": FormulaDefinition(
        "기본 월 잔여금",
        (
            "세후 월 소득 - 비주거·교통 생활비 - 기존대출 월 상환액 "
            "- 월 주거·교통비"
        ),
        {
            "세후 월 소득": "analysis.cash_flow.after_tax_monthly_income",
            "비주거·교통 생활비": (
                "analysis.cash_flow."
                "monthly_living_expenses_excluding_housing_and_transport"
            ),
            "기존대출 월 상환액": (
                "analysis.cash_flow.existing_loan_monthly_payment"
            ),
            "월 주거·교통비": (
                "candidate.monthly_cash_flow."
                "monthly_housing_and_transport_cost"
            ),
        },
        "candidate.calculation_details.base_monthly_balance",
    ),
    "actual_monthly_balance": FormulaDefinition(
        "실제 월 잔여금",
        "기본 월 잔여금 - 목표 월 저축액",
        {
            "기본 월 잔여금": (
                "candidate.calculation_details.base_monthly_balance"
            ),
            "목표 월 저축액": (
                "analysis.financial_goals.target_monthly_savings"
            ),
        },
        "candidate.monthly_cash_flow.actual_monthly_balance",
    ),
    "monthly_budget_margin": FormulaDefinition(
        "월 예산 여유액",
        "실제 월 잔여금 - 월 안전여유",
        {
            "실제 월 잔여금": (
                "candidate.monthly_cash_flow.actual_monthly_balance"
            ),
            "월 안전여유": (
                "analysis.financial_goals.monthly_safety_margin"
            ),
        },
        "candidate.monthly_cash_flow.monthly_budget_margin",
    ),
    "annual_financial_target": FormulaDefinition(
        "1년 재무목표액",
        "최소 비상자금 + 12 × 목표 월 저축액",
        {
            "최소 비상자금": (
                "analysis.financial_goals.minimum_emergency_fund"
            ),
            "목표 월 저축액": (
                "analysis.financial_goals.target_monthly_savings"
            ),
        },
        "candidate.annual_goal.annual_financial_target",
    ),
    "expected_resources_after_one_year": FormulaDefinition(
        "1년 후 예상 재무자원",
        (
            "입주 후 유동자산 + 계약 후 회수되는 기존 임차보증금 "
            "+ 12 × (목표 월 저축액 + 실제 월 잔여금)"
        ),
        {
            "입주 후 유동자산": (
                "candidate.initial_funds.post_move_liquid_assets"
            ),
            "계약 후 회수되는 기존 임차보증금": (
                "candidate.calculation_details.deferred_existing_deposit"
            ),
            "목표 월 저축액": (
                "analysis.financial_goals.target_monthly_savings"
            ),
            "실제 월 잔여금": (
                "candidate.monthly_cash_flow.actual_monthly_balance"
            ),
        },
        "candidate.annual_goal.expected_resources_after_one_year",
        note=(
            "계약일 전에 회수할 수 없어 초기자금에서 제외한 기존 "
            "임차보증금은 1년 후 예상 재무자원에 포함합니다."
        ),
    ),
    "annual_financial_surplus": FormulaDefinition(
        "1년 재무 여유·부족액",
        "1년 후 예상 재무자원 - 1년 재무목표액",
        {
            "1년 후 예상 재무자원": (
                "candidate.annual_goal.expected_resources_after_one_year"
            ),
            "1년 재무목표액": (
                "candidate.annual_goal.annual_financial_target"
            ),
        },
        "candidate.annual_goal.annual_financial_surplus",
    ),
    "annual_goal_achievement_rate": FormulaDefinition(
        "재무목표 달성률",
        "1년 후 예상 재무자원 ÷ 1년 재무목표액 × 100",
        {
            "1년 후 예상 재무자원": (
                "candidate.annual_goal.expected_resources_after_one_year"
            ),
            "1년 재무목표액": (
                "candidate.annual_goal.annual_financial_target"
            ),
        },
        "candidate.annual_goal.annual_goal_achievement_rate",
        "소수점 둘째 자리 반올림",
        "목표액이 0원이면 예상 자원이 0원 이상일 때 100%입니다.",
    ),
    "equivalent_monthly_cost": FormulaDefinition(
        "환산 월 임대비용",
        "월세 + 보증금 × 연 전월세전환율 ÷ 100 ÷ 12",
        {
            "월세": "housing.monthly_rent",
            "보증금": "housing.deposit",
        },
        (
            "candidate.price_appropriateness."
            "candidate_equivalent_monthly_cost"
        ),
        "원 단위 반올림(ROUND_HALF_UP)",
        "연 전월세전환율은 지역·주택 유형별 외부 통계값을 사용합니다.",
    ),
    "difference_from_median": FormulaDefinition(
        "중앙값과의 가격 차액",
        "후보 매물 환산 월 임대비용 - 비교 표본 중앙값",
        {
            "비교 표본 중앙값": (
                "candidate.price_appropriateness."
                "median_equivalent_monthly_cost"
            ),
        },
        "candidate.price_appropriateness.difference_from_median",
    ),
    "difference_rate_from_median": FormulaDefinition(
        "중앙값과의 가격 차이율",
        "중앙값과의 가격 차액 ÷ 비교 표본 중앙값 × 100",
        {
            "중앙값과의 가격 차액": (
                "candidate.price_appropriateness.difference_from_median"
            ),
            "비교 표본 중앙값": (
                "candidate.price_appropriateness."
                "median_equivalent_monthly_cost"
            ),
        },
        "candidate.price_appropriateness.difference_rate_from_median",
        "소수점 둘째 자리 반올림",
    ),
    "price_percentile": FormulaDefinition(
        "가격 백분위",
        "후보 매물 이하인 비교 표본 수 ÷ 전체 비교 표본 수 × 100",
        {
            "전체 비교 표본 수": (
                "candidate.price_appropriateness.sample_count"
            ),
        },
        "candidate.price_appropriateness.price_percentile",
        "소수점 둘째 자리 반올림",
    ),
}


def calculation_formula(metric: str) -> dict[str, Any]:
    definition = FORMULAS.get(metric)
    if definition is None:
        return {
            "status": "unknown_metric",
            "metric": metric,
            "available_metrics": sorted(FORMULAS),
        }
    return {
        "status": "available",
        "metric": metric,
        "label": definition.label,
        "formula": definition.formula,
        "variables": list(definition.operands),
        "rounding": definition.rounding,
        "note": definition.note,
    }


def calculation_breakdown(
    analysis_context: dict[str, Any],
    property_id: str,
    metric: str,
) -> dict[str, Any]:
    formula = calculation_formula(metric)
    if formula["status"] != "available":
        return formula

    analysis = analysis_context.get("analysis") or {}
    evaluation = analysis_context.get("evaluation") or {}
    housing = _find_by_property_id(
        analysis.get("housing_plans", []),
        property_id,
    )
    candidate = _find_by_property_id(
        evaluation.get("candidates", []),
        property_id,
    )
    if housing is None:
        return {
            **formula,
            "status": "housing_plan_not_found",
            "property_id": property_id,
        }
    if candidate is None:
        return {
            **formula,
            "status": "evaluation_not_available",
            "property_id": property_id,
        }

    sources = {
        "analysis": analysis,
        "housing": housing,
        "candidate": candidate,
    }
    definition = FORMULAS[metric]
    operands = {
        label: _resolve_path(sources, path)
        for label, path in definition.operands.items()
    }
    return {
        **formula,
        "property_id": property_id,
        "property_name": housing.get("name"),
        "operands": operands,
        "result": _resolve_path(sources, definition.result_path),
    }


def _find_by_property_id(
    items: list[dict[str, Any]],
    property_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in items
            if str(item.get("property_id")) == str(property_id)
        ),
        None,
    )


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
