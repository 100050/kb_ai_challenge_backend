from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.models.analysis import Analysis
from app.models.housing_plan import HousingPlan
from app.ai.interpretation import AIInterpretationGenerator
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


PRICE_REFRESH_INTERVAL = timedelta(hours=24)


class EvaluationService:
    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        housing_plan_repository: HousingPlanRepository,
        evaluation_repository: EvaluationRepository,
        market_price_service: MarketPriceService,
        interpretation_generator: AIInterpretationGenerator | None = None,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.housing_plan_repository = housing_plan_repository
        self.evaluation_repository = evaluation_repository
        self.market_price_service = market_price_service
        self.interpretation_generator = interpretation_generator

    async def evaluate(self, analysis_id: UUID) -> EvaluationStarted | None:
        analysis = await self.analysis_repository.get(analysis_id)
        if analysis is None:
            return None
        previous_evaluation = await self.evaluation_repository.get(
            analysis_id,
        )
        if (
            previous_evaluation is not None
            and previous_evaluation.status == "completed"
            and previous_evaluation.result is not None
            and previous_evaluation.result.get("result_version") == 3
        ):
            generated_at = self._result_generated_at(
                previous_evaluation.result,
            )
            if (
                generated_at is not None
                and datetime.now(timezone.utc) - generated_at
                < PRICE_REFRESH_INTERVAL
            ):
                return EvaluationStarted(
                    evaluation_id=previous_evaluation.id,
                    status="completed",
                    progress=100,
                )
            refreshed = await self._refresh_prices(
                analysis_id,
                previous_evaluation.result,
            )
            if refreshed is not None:
                evaluation = await self.evaluation_repository.save_completed(
                    analysis_id,
                    refreshed,
                )
                return EvaluationStarted(
                    evaluation_id=evaluation.id,
                    status="completed",
                    progress=100,
                )
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

        interpretations = await self._generate_interpretations(
            [candidate.model_dump(mode="json") for candidate in candidates],
        )
        candidates = [
            candidate.model_copy(
                update={
                    "ai_interpretation": interpretations.get(
                        str(candidate.property_id),
                    ),
                },
            )
            for candidate in candidates
        ]

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

    async def _refresh_prices(
        self,
        analysis_id: UUID,
        previous_result: dict,
    ) -> dict | None:
        plans = await self.housing_plan_repository.list(analysis_id)
        candidates = previous_result.get("candidates")
        if not isinstance(candidates, list):
            return None
        candidates_by_property_id = {
            str(candidate.get("property_id")): candidate
            for candidate in candidates
            if isinstance(candidate, dict)
        }
        if set(candidates_by_property_id) != {
            str(plan.id) for plan in plans
        }:
            return None

        refreshed_result = deepcopy(previous_result)
        refreshed_candidates = {
            str(candidate["property_id"]): candidate
            for candidate in refreshed_result["candidates"]
        }
        for plan in plans:
            price_result = await self.market_price_service.evaluate_safely(plan)
            refreshed_candidates[str(plan.id)]["price_appropriateness"] = (
                price_result.model_dump(mode="json")
            )
        for candidate in refreshed_result["candidates"]:
            candidate["ai_interpretation"] = None
        interpretations = await self._generate_interpretations(
            refreshed_result["candidates"],
        )
        for property_id, interpretation in interpretations.items():
            refreshed_candidates[property_id]["ai_interpretation"] = (
                interpretation.model_dump(mode="json")
            )
        refreshed_result["generated_at"] = datetime.now(
            timezone.utc,
        ).isoformat()
        return refreshed_result

    async def _generate_interpretations(
        self,
        candidates: list[dict],
    ) -> dict:
        if self.interpretation_generator is None:
            return {}
        try:
            return await self.interpretation_generator.generate(candidates)
        except Exception:
            return {}

    @staticmethod
    def _result_generated_at(result: dict) -> datetime | None:
        value = result.get("generated_at")
        if isinstance(value, datetime):
            generated_at = value
        elif isinstance(value, str):
            try:
                generated_at = datetime.fromisoformat(
                    value.replace("Z", "+00:00"),
                )
            except ValueError:
                return None
        else:
            return None
        if generated_at.tzinfo is None:
            return generated_at.replace(tzinfo=timezone.utc)
        return generated_at.astimezone(timezone.utc)

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
            "existing_rental_deposit_available_before_contract",
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
            existing_rental_deposit_available_before_contract=(
                analysis.existing_rental_deposit_available_before_contract
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
