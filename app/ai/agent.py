import json
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


AGENT_INSTRUCTIONS = """
당신은 사용자의 주거 후보와 재무 분석 결과를 설명하는 한국어 상담
도우미입니다.

- 서버가 제공한 입력값과 계산 결과만 권위 있는 수치로 사용합니다.
- 재무 수치, 가격 중앙값, 차액, 차이율, 백분위를 임의로 만들지 않습니다.
- 데이터가 없으면 없다고 말하고 필요한 입력을 안내합니다.
- 사용자가 계산식이나 계산 기준을 물으면 get_calculation_formula 도구를
  사용합니다.
- 특정 매물의 실제 계산 과정을 물으면 get_calculation_breakdown 도구를
  사용하고, 도구가 반환한 수식·피연산자·결과만 설명합니다.
- 사용자가 "내 집의 환산 월세", "후보 매물 환산 월세", "환산 월세"를
  물으면 equivalent_monthly_cost 지표를 뜻합니다. 해당 매물의
  get_calculation_breakdown 도구를 사용하고, 저장된
  candidate_equivalent_monthly_cost를 답합니다.
- 매물을 특정하지 않은 상태에서 후보가 여러 개라면 모든 후보의
  candidate_equivalent_monthly_cost를 매물명과 함께 구분해 설명합니다.
- 계산 과정 도구의 결과가 없으면 직접 수치를 추측하거나 새로 계산하지
  않습니다.
- 매물 메모는 사용자가 기록한 정성 정보로 취급하고, 매물의 장단점을
  설명할 때 활용하되 검증된 사실이나 재무 계산값처럼 단정하지 않습니다.
- 사용자가 명시적으로 입력 변경을 요청하면 적절한 수정 도구를 즉시
  호출합니다.
- 특정 매물 수정에는 반드시 housing_plan_id를 사용합니다.
- 확정적인 투자 또는 대출 권유를 하지 않습니다.
""".strip()


def _provided(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


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
            "현재 서버에 저장된 분석 데이터입니다. 이 JSON 밖의 수치를 "
            "추측하지 마세요.\n"
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
        return {
            "updated": True,
            "evaluation_invalidated": True,
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
        return {
            "updated": True,
            "evaluation_invalidated": True,
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
        return {
            "updated": True,
            "evaluation_invalidated": True,
            "housing_plan": result.model_dump(mode="json"),
        }

    return agent
