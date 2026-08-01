import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from app.ai.dependencies import ChatDependencies
from app.schemas.analysis_input import CashFlowUpdate, FinancialGoalsUpdate
from app.schemas.housing_plan import HousingPlanUpdate
from app.services.calculation_explanations import (
    CalculationMetric,
    calculation_breakdown,
    calculation_formula,
)
from app.services.evaluation import AnalysisNotReady


PROMPT_PATH = Path(__file__).with_name("prompt")
AGENT_INSTRUCTIONS = PROMPT_PATH.read_text(encoding="utf-8").strip()


def _provided(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


async def _regenerate_evaluation(
    ctx: RunContext[ChatDependencies],
) -> dict[str, Any]:
    try:
        evaluation = await ctx.deps.evaluation_service.evaluate(
            ctx.deps.analysis_id,
        )
    except AnalysisNotReady as exc:
        return {
            "evaluation_regenerated": False,
            "reason": "analysis_not_ready",
            "details": exc.details,
        }
    if evaluation is None:
        return {
            "evaluation_regenerated": False,
            "reason": "analysis_not_found",
        }
    evaluation_result = await ctx.deps.evaluation_service.get_result(
        ctx.deps.analysis_id,
    )
    return {
        "evaluation_regenerated": True,
        "evaluation_id": str(evaluation.evaluation_id),
        "evaluation_status": evaluation.status,
        "evaluation_progress": evaluation.progress,
        "evaluation_result": (
            evaluation_result.model_dump(mode="json")
            if evaluation_result is not None
            else None
        ),
    }


def create_chat_agent(
    model: Model,
) -> Agent[ChatDependencies, str]:
    agent = Agent(
        model,
        deps_type=ChatDependencies,
        output_type=str,
        instructions=AGENT_INSTRUCTIONS,
    )

    @agent.instructions
    def analysis_context(ctx: RunContext[ChatDependencies]) -> str:
        return (
            "ANALYSIS_CONTEXT:\n"
            + json.dumps(
                ctx.deps.analysis_context,
                ensure_ascii=False,
                default=str,
            )
        )

    @agent.tool
    async def get_calculation_formula(
        ctx: RunContext[ChatDependencies],
        metric: CalculationMetric,
    ) -> dict[str, Any]:
        """재무 및 가격 적정성 지표의 공식 계산식과 변수 의미를 조회합니다."""
        return calculation_formula(metric)

    @agent.tool
    async def get_calculation_breakdown(
        ctx: RunContext[ChatDependencies],
        housing_plan_id: UUID,
        metric: CalculationMetric,
    ) -> dict[str, Any]:
        """특정 후보 매물 지표의 수식, 실제 피연산자와 저장된 결과를 조회합니다."""
        return calculation_breakdown(
            ctx.deps.analysis_context,
            str(housing_plan_id),
            metric,
        )

    @agent.tool
    async def update_cash_flow(
        ctx: RunContext[ChatDependencies],
        after_tax_monthly_income: int | None = None,
        monthly_living_expenses_excluding_housing_and_transport: (
            int | None
        ) = None,
        existing_loan_monthly_payment: int | None = None,
    ) -> dict[str, Any]:
        """소득과 생활비 입력 중 사용자가 요청한 필드만 수정합니다."""
        payload = CashFlowUpdate.model_validate(
            _provided(
                after_tax_monthly_income=after_tax_monthly_income,
                monthly_living_expenses_excluding_housing_and_transport=(
                    monthly_living_expenses_excluding_housing_and_transport
                ),
                existing_loan_monthly_payment=existing_loan_monthly_payment,
            ),
        )
        result = await ctx.deps.analysis_service.update_cash_flow(
            ctx.deps.analysis_id,
            payload,
        )
        if result is None:
            return {"updated": False, "reason": "analysis_not_found"}
        evaluation = await _regenerate_evaluation(ctx)
        return {
            "updated": True,
            **evaluation,
            "cash_flow": result.model_dump(mode="json"),
        }

    @agent.tool
    async def update_financial_goals(
        ctx: RunContext[ChatDependencies],
        target_monthly_savings: int | None = None,
        monthly_safety_margin: int | None = None,
        available_cash: int | None = None,
        minimum_emergency_fund: int | None = None,
        recoverable_existing_rental_deposit: int | None = None,
        existing_rental_deposit_available_before_contract: (
            bool | None
        ) = None,
    ) -> dict[str, Any]:
        """자산과 재무 목표 입력 중 요청한 필드만 수정합니다."""
        payload = FinancialGoalsUpdate.model_validate(
            _provided(
                target_monthly_savings=target_monthly_savings,
                monthly_safety_margin=monthly_safety_margin,
                available_cash=available_cash,
                minimum_emergency_fund=minimum_emergency_fund,
                recoverable_existing_rental_deposit=(
                    recoverable_existing_rental_deposit
                ),
                existing_rental_deposit_available_before_contract=(
                    existing_rental_deposit_available_before_contract
                ),
            ),
        )
        result = await ctx.deps.analysis_service.update_financial_goals(
            ctx.deps.analysis_id,
            payload,
        )
        if result is None:
            return {"updated": False, "reason": "analysis_not_found"}
        evaluation = await _regenerate_evaluation(ctx)
        return {
            "updated": True,
            **evaluation,
            "financial_goals": result.model_dump(mode="json"),
        }

    @agent.tool
    async def update_housing_plan(
        ctx: RunContext[ChatDependencies],
        housing_plan_id: UUID,
        name: str | None = None,
        memo: str | None = None,
        address: str | None = None,
        deposit: int | None = None,
        monthly_rent: int | None = None,
        maintenance_fee: int | None = None,
        utilities: int | None = None,
        transportation_cost: int | None = None,
        deposit_loan_amount: int | None = None,
        annual_interest_rate: float | None = None,
        brokerage_fee: int | None = None,
        moving_cost: int | None = None,
        other_move_in_cost: int | None = None,
    ) -> dict[str, Any]:
        """후보 매물과 해당 매물의 대출·입주비 입력을 수정합니다."""
        values = _provided(
            name=name,
            memo=memo,
            address=address,
            deposit=deposit,
            monthly_rent=monthly_rent,
            maintenance_fee=maintenance_fee,
            utilities=utilities,
            transportation_cost=transportation_cost,
        )
        loan = _provided(
            deposit_loan_amount=deposit_loan_amount,
            annual_interest_rate=annual_interest_rate,
        )
        costs = _provided(
            brokerage_fee=brokerage_fee,
            moving_cost=moving_cost,
            other_move_in_cost=other_move_in_cost,
        )
        if loan:
            current = await ctx.deps.analysis_service.get_housing_plan(
                ctx.deps.analysis_id,
                housing_plan_id,
            )
            if current is None:
                return {"updated": False, "reason": "housing_plan_not_found"}
            current_loan = (
                current.loan_plan.model_dump()
                if current.loan_plan is not None
                else {}
            )
            values["loan_plan"] = {**current_loan, **loan}
        if costs:
            current = await ctx.deps.analysis_service.get_housing_plan(
                ctx.deps.analysis_id,
                housing_plan_id,
            )
            if current is None:
                return {"updated": False, "reason": "housing_plan_not_found"}
            current_costs = (
                current.additional_costs.model_dump()
                if current.additional_costs is not None
                else {}
            )
            values["additional_costs"] = {**current_costs, **costs}

        payload = HousingPlanUpdate.model_validate(values)
        result = await ctx.deps.analysis_service.update_housing_plan(
            ctx.deps.analysis_id,
            housing_plan_id,
            payload,
        )
        if result is None:
            return {"updated": False, "reason": "housing_plan_not_found"}
        evaluation = await _regenerate_evaluation(ctx)
        return {
            "updated": True,
            **evaluation,
            "housing_plan": result.model_dump(mode="json"),
        }

    return agent
