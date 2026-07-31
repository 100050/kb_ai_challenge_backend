from datetime import datetime, timezone
from uuid import UUID

from app.models.analysis import Analysis
from app.models.housing_plan import HousingPlan
from app.repositories.analysis import AnalysisRepository
from app.repositories.evaluation import EvaluationRepository
from app.repositories.housing_plan import HousingPlanRepository
from app.schemas.analysis import AnalysisDetail, AnalysisSummary
from app.schemas.analysis_input import (
    CashFlow,
    CashFlowResponse,
    CashFlowUpdate,
    FinancialGoals,
    FinancialGoalsResponse,
    FinancialGoalsUpdate,
)
from app.schemas.housing_plan import (
    AdditionalCosts,
    HousingPlanCreate,
    HousingPlanResponse,
    HousingPlanSummary,
    HousingPlanUpdate,
    LoanPlan,
)


class HousingPlanLimitReached(Exception):
    pass


class AnalysisService:
    def __init__(
        self,
        repository: AnalysisRepository,
        housing_plan_repository: HousingPlanRepository,
        evaluation_repository: EvaluationRepository,
        *,
        max_housing_plans: int,
    ) -> None:
        self.repository = repository
        self.housing_plan_repository = housing_plan_repository
        self.evaluation_repository = evaluation_repository
        self.max_housing_plans = max_housing_plans

    async def create(self) -> AnalysisSummary:
        analysis = await self.repository.create()
        return self._summary(analysis)

    async def get(self, analysis_id: UUID) -> AnalysisDetail | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None
        plans = await self.housing_plan_repository.list(analysis_id)
        return self._detail(analysis, plans)

    async def delete(self, analysis_id: UUID) -> bool:
        return await self.repository.delete(analysis_id)

    async def update_cash_flow(
        self,
        analysis_id: UUID,
        payload: CashFlowUpdate,
    ) -> CashFlowResponse | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(analysis, field, value)

        plans = await self.housing_plan_repository.list(analysis_id)
        self._update_progress(analysis, plans)
        await self.evaluation_repository.delete(analysis_id)
        await self.repository.save(analysis)
        return self._cash_flow_response(analysis)

    async def update_financial_goals(
        self,
        analysis_id: UUID,
        payload: FinancialGoalsUpdate,
    ) -> FinancialGoalsResponse | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(analysis, field, value)

        plans = await self.housing_plan_repository.list(analysis_id)
        self._update_progress(analysis, plans)
        await self.evaluation_repository.delete(analysis_id)
        await self.repository.save(analysis)
        return self._financial_goals_response(analysis)

    async def create_housing_plan(
        self,
        analysis_id: UUID,
        payload: HousingPlanCreate,
    ) -> HousingPlanResponse | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None

        plans = await self.housing_plan_repository.list(analysis_id)
        if len(plans) >= self.max_housing_plans:
            raise HousingPlanLimitReached

        housing_plan = await self.housing_plan_repository.create(analysis_id)
        self._apply_housing_plan_update(housing_plan, payload)
        plans.append(housing_plan)
        self._update_progress(analysis, plans)
        await self.evaluation_repository.delete(analysis_id)
        await self.repository.save(analysis)
        return self._housing_plan_response(housing_plan)

    async def list_housing_plans(
        self,
        analysis_id: UUID,
    ) -> list[HousingPlanSummary] | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None
        plans = await self.housing_plan_repository.list(analysis_id)
        return [self._housing_plan_summary(plan) for plan in plans]

    async def get_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
    ) -> HousingPlanResponse | None:
        housing_plan = await self.housing_plan_repository.get(
            analysis_id,
            property_id,
        )
        if housing_plan is None:
            return None
        return self._housing_plan_response(housing_plan)

    async def update_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
        payload: HousingPlanUpdate,
    ) -> HousingPlanResponse | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None
        housing_plan = await self.housing_plan_repository.get(
            analysis_id,
            property_id,
        )
        if housing_plan is None:
            return None

        self._apply_housing_plan_update(housing_plan, payload)
        plans = await self.housing_plan_repository.list(analysis_id)
        self._update_progress(analysis, plans)
        await self.evaluation_repository.delete(analysis_id)
        await self.repository.save(analysis)
        return self._housing_plan_response(housing_plan)

    async def delete_housing_plan(
        self,
        analysis_id: UUID,
        property_id: UUID,
    ) -> bool:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return False
        housing_plan = await self.housing_plan_repository.get(
            analysis_id,
            property_id,
        )
        if housing_plan is None:
            return False

        await self.housing_plan_repository.delete(housing_plan)
        plans = await self.housing_plan_repository.list(analysis_id)
        self._update_progress(analysis, plans)
        await self.evaluation_repository.delete(analysis_id)
        await self.repository.save(analysis)
        return True

    @staticmethod
    def _apply_housing_plan_update(
        housing_plan: HousingPlan,
        payload: HousingPlanCreate | HousingPlanUpdate,
    ) -> None:
        updates = payload.model_dump(exclude_unset=True)
        has_loan_plan = "loan_plan" in updates
        has_additional_costs = "additional_costs" in updates
        loan_plan = updates.pop("loan_plan", None)
        additional_costs = updates.pop("additional_costs", None)

        for field, value in updates.items():
            setattr(housing_plan, field, value)

        if has_loan_plan:
            if loan_plan is None:
                housing_plan.deposit_loan_amount = None
                housing_plan.annual_interest_rate = None
            else:
                housing_plan.deposit_loan_amount = loan_plan[
                    "deposit_loan_amount"
                ]
                housing_plan.annual_interest_rate = loan_plan[
                    "annual_interest_rate"
                ]

        if has_additional_costs:
            if additional_costs is None:
                housing_plan.brokerage_fee = None
                housing_plan.moving_cost = None
                housing_plan.other_move_in_cost = None
            else:
                housing_plan.brokerage_fee = additional_costs[
                    "brokerage_fee"
                ]
                housing_plan.moving_cost = additional_costs["moving_cost"]
                housing_plan.other_move_in_cost = additional_costs[
                    "other_move_in_cost"
                ]

        housing_plan.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _update_progress(
        analysis: Analysis,
        housing_plans: list[HousingPlan],
    ) -> None:
        cash_flow_complete = all(
            value is not None
            for value in (
                analysis.after_tax_monthly_income,
                analysis.monthly_living_expenses_excluding_housing_and_transport,
                analysis.existing_loan_monthly_payment,
            )
        )
        financial_goals_complete = all(
            value is not None
            for value in (
                analysis.target_monthly_savings,
                analysis.monthly_safety_margin,
                analysis.available_cash,
                analysis.minimum_emergency_fund,
                analysis.recoverable_existing_rental_deposit,
                analysis.existing_rental_deposit_available_before_contract,
            )
        )
        housing_plans_complete = bool(housing_plans) and all(
            plan.is_complete for plan in housing_plans
        )

        if not cash_flow_complete:
            analysis.current_step = "cash_flow"
            analysis.progress = 0
        elif not financial_goals_complete:
            analysis.current_step = "financial_goals"
            analysis.progress = 33
        elif not housing_plans_complete:
            analysis.current_step = "housing_plan"
            analysis.progress = 67
        else:
            analysis.current_step = "confirmation"
            analysis.progress = 100
        analysis.status = "draft"
        analysis.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _summary(analysis: Analysis) -> AnalysisSummary:
        return AnalysisSummary(
            analysis_id=analysis.id,
            status=analysis.status,
            current_step=analysis.current_step,
            progress=analysis.progress,
            created_at=analysis.created_at,
        )

    @classmethod
    def _detail(
        cls,
        analysis: Analysis,
        plans: list[HousingPlan],
    ) -> AnalysisDetail:
        cash_flow = cls._cash_flow(analysis)
        financial_goals = cls._financial_goals(analysis)
        return AnalysisDetail(
            analysis_id=analysis.id,
            status=analysis.status,
            current_step=analysis.current_step,
            progress=analysis.progress,
            cash_flow=(
                cash_flow
                if any(
                    value is not None
                    for value in cash_flow.model_dump().values()
                )
                else None
            ),
            financial_goals=(
                financial_goals
                if any(
                    value is not None
                    for value in financial_goals.model_dump().values()
                )
                else None
            ),
            housing_plans=[cls._housing_plan_summary(plan) for plan in plans],
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    @classmethod
    def _cash_flow_response(cls, analysis: Analysis) -> CashFlowResponse:
        return CashFlowResponse(
            analysis_id=analysis.id,
            cash_flow=cls._cash_flow(analysis),
            current_step=analysis.current_step,
            progress=analysis.progress,
        )

    @staticmethod
    def _cash_flow(analysis: Analysis) -> CashFlow:
        return CashFlow(
            after_tax_monthly_income=analysis.after_tax_monthly_income,
            monthly_living_expenses_excluding_housing_and_transport=(
                analysis.monthly_living_expenses_excluding_housing_and_transport
            ),
            existing_loan_monthly_payment=(
                analysis.existing_loan_monthly_payment
            ),
        )

    @classmethod
    def _financial_goals_response(
        cls,
        analysis: Analysis,
    ) -> FinancialGoalsResponse:
        return FinancialGoalsResponse(
            analysis_id=analysis.id,
            financial_goals=cls._financial_goals(analysis),
            current_step=analysis.current_step,
            progress=analysis.progress,
        )

    @staticmethod
    def _financial_goals(analysis: Analysis) -> FinancialGoals:
        return FinancialGoals(
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
    def _housing_plan_response(
        housing_plan: HousingPlan,
    ) -> HousingPlanResponse:
        loan_plan = None
        if (
            housing_plan.deposit_loan_amount is not None
            and housing_plan.annual_interest_rate is not None
        ):
            loan_plan = LoanPlan(
                deposit_loan_amount=housing_plan.deposit_loan_amount,
                annual_interest_rate=housing_plan.annual_interest_rate,
            )

        additional_costs = None
        if all(
            value is not None
            for value in (
                housing_plan.brokerage_fee,
                housing_plan.moving_cost,
                housing_plan.other_move_in_cost,
            )
        ):
            additional_costs = AdditionalCosts(
                brokerage_fee=housing_plan.brokerage_fee,
                moving_cost=housing_plan.moving_cost,
                other_move_in_cost=housing_plan.other_move_in_cost,
            )

        return HousingPlanResponse(
            analysis_id=housing_plan.analysis_id,
            property_id=housing_plan.id,
            name=housing_plan.name,
            memo=housing_plan.memo,
            address=housing_plan.address,
            property_type=housing_plan.property_type,
            legal_dong_code=housing_plan.legal_dong_code,
            exclusive_area_m2=housing_plan.exclusive_area_m2,
            housing_type=housing_plan.housing_type,
            deposit=housing_plan.deposit,
            monthly_rent=housing_plan.monthly_rent,
            maintenance_fee=housing_plan.maintenance_fee,
            utilities=housing_plan.utilities,
            transportation_cost=housing_plan.transportation_cost,
            loan_plan=loan_plan,
            additional_costs=additional_costs,
            is_complete=housing_plan.is_complete,
            created_at=housing_plan.created_at,
            updated_at=housing_plan.updated_at,
        )

    @staticmethod
    def _housing_plan_summary(
        housing_plan: HousingPlan,
    ) -> HousingPlanSummary:
        return HousingPlanSummary(
            property_id=housing_plan.id,
            name=housing_plan.name,
            memo=housing_plan.memo,
            housing_type=housing_plan.housing_type,
            is_complete=housing_plan.is_complete,
            updated_at=housing_plan.updated_at,
        )
