from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.models.analysis import Analysis
from app.models.housing_plan import HousingPlan
from app.repositories.analysis import AnalysisRepository
from app.repositories.evaluation import EvaluationRepository
from app.repositories.housing_plan import HousingPlanRepository
from app.schemas.evaluation import (
    CommonFinancialInput,
    EvaluationStarted,
    EvaluationStatus,
    FinancialEvaluationResult,
    PropertyFinancialInput,
)
from app.services.financial_calculations import evaluate_property
from app.services.market_price import MarketPriceService


class AnalysisNotReady(Exception):
    def __init__(self, details: list[dict[str, str]]) -> None:
        self.details = details


class EvaluationService:
    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        housing_plan_repository: HousingPlanRepository,
        evaluation_repository: EvaluationRepository,
        market_price_service: MarketPriceService,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.housing_plan_repository = housing_plan_repository
        self.evaluation_repository = evaluation_repository
        self.market_price_service = market_price_service

    async def evaluate(self, analysis_id: UUID) -> EvaluationStarted | None:
        analysis = await self.analysis_repository.get(analysis_id)
        if analysis is None:
            return None
        plans = await self.housing_plan_repository.list(analysis_id)
        details = self._readiness_errors(analysis, plans)
        if details:
            raise AnalysisNotReady(details)

        common = self._common_input(analysis)
        candidates = []
        for plan in plans:
            financial_result = evaluate_property(
                common,
                self._property_input(plan),
            )
            price_result = await self.market_price_service.evaluate_safely(plan)
            candidates.append(
                financial_result.model_copy(
                    update={"price_appropriateness": price_result},
                ),
            )

        result = FinancialEvaluationResult(
            analysis_id=analysis_id,
            candidates=candidates,
            generated_at=datetime.now(timezone.utc),
        )
        evaluation = await self.evaluation_repository.save_completed(
            analysis_id,
            result.model_dump(mode="json"),
        )
        analysis.status = "completed"
        await self.analysis_repository.save(analysis)
        return EvaluationStarted(
            evaluation_id=evaluation.id,
            status="completed",
            progress=100,
        )

    async def get_status(self, analysis_id: UUID) -> EvaluationStatus | None:
        evaluation = await self.evaluation_repository.get(analysis_id)
        if evaluation is None:
            return None
        return EvaluationStatus(
            evaluation_id=evaluation.id,
            status=evaluation.status,
            current_stage=evaluation.current_stage,
            progress=evaluation.progress,
            error=evaluation.error,
            updated_at=evaluation.updated_at,
        )

    async def get_result(
        self,
        analysis_id: UUID,
    ) -> FinancialEvaluationResult | None:
        evaluation = await self.evaluation_repository.get(analysis_id)
        if evaluation is None or evaluation.result is None:
            return None
        return FinancialEvaluationResult.model_validate(evaluation.result)

    @staticmethod
    def _readiness_errors(
        analysis: Analysis,
        plans: list[HousingPlan],
    ) -> list[dict[str, str]]:
        details: list[dict[str, str]] = []
        common_fields = (
            "after_tax_monthly_income",
            "monthly_living_expenses_excluding_housing_and_transport",
            "existing_loan_monthly_payment",
            "target_monthly_savings",
            "monthly_safety_margin",
            "available_cash",
            "minimum_emergency_fund",
            "recoverable_existing_rental_deposit",
        )
        for field in common_fields:
            if getattr(analysis, field) is None:
                details.append(
                    {
                        "field": field,
                        "reason": "필수 입력값입니다.",
                    },
                )

        if not plans:
            details.append(
                {
                    "field": "housing_plans",
                    "reason": "완성된 매물이 1개 이상 필요합니다.",
                },
            )
        for index, plan in enumerate(plans):
            if not plan.is_complete:
                details.append(
                    {
                        "field": f"housing_plans.{index}",
                        "reason": "매물 입력을 완료해 주세요.",
                    },
                )
            elif plan.deposit_loan_amount > plan.deposit:
                details.append(
                    {
                        "field": (
                            f"housing_plans.{index}."
                            "loan_plan.deposit_loan_amount"
                        ),
                        "reason": "보증금 대출액은 보증금을 초과할 수 없습니다.",
                    },
                )
        return details

    @staticmethod
    def _common_input(analysis: Analysis) -> CommonFinancialInput:
        return CommonFinancialInput(
            after_tax_monthly_income=analysis.after_tax_monthly_income,
            monthly_living_expenses_excluding_housing_and_transport=(
                analysis.monthly_living_expenses_excluding_housing_and_transport
            ),
            existing_loan_monthly_payment=(
                analysis.existing_loan_monthly_payment
            ),
            target_monthly_savings=analysis.target_monthly_savings,
            monthly_safety_margin=analysis.monthly_safety_margin,
            available_cash=analysis.available_cash,
            minimum_emergency_fund=analysis.minimum_emergency_fund,
            recoverable_existing_rental_deposit=(
                analysis.recoverable_existing_rental_deposit
            ),
        )

    @staticmethod
    def _property_input(plan: HousingPlan) -> PropertyFinancialInput:
        return PropertyFinancialInput(
            property_id=plan.id,
            name=plan.name,
            memo=plan.memo,
            deposit=plan.deposit,
            monthly_rent=plan.monthly_rent,
            maintenance_fee=plan.maintenance_fee,
            utilities=plan.utilities,
            transportation_cost=plan.transportation_cost,
            deposit_loan_amount=plan.deposit_loan_amount,
            annual_interest_rate=Decimal(str(plan.annual_interest_rate)),
            brokerage_fee=plan.brokerage_fee,
            moving_cost=plan.moving_cost,
            other_move_in_cost=plan.other_move_in_cost,
        )
