import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.analysis import Analysis
from app.models.evaluation import Evaluation
from app.models.housing_plan import HousingPlan
from app.schemas.evaluation import (
    AIInsightCard,
    AIInterpretation,
    PriceAppropriatenessResult,
)
from app.services.evaluation import EvaluationService


class AnalysisRepositoryStub:
    def __init__(self, analysis: Analysis) -> None:
        self.analysis = analysis

    async def get(self, analysis_id):
        return self.analysis if analysis_id == self.analysis.id else None


class HousingPlanRepositorySpy:
    async def list(self, analysis_id):
        raise AssertionError("cached evaluation must not reload housing plans")


class EvaluationRepositoryStub:
    def __init__(self, evaluation: Evaluation) -> None:
        self.evaluation = evaluation

    async def get(self, analysis_id):
        if analysis_id == self.evaluation.analysis_id:
            return self.evaluation
        return None

    async def save_completed(self, analysis_id, result):
        self.evaluation.result = result
        return self.evaluation


class MarketPriceServiceSpy:
    async def evaluate_safely(self, plan):
        raise AssertionError("cached evaluation must not call external APIs")


class HousingPlanRepositoryStub:
    def __init__(self, plans):
        self.plans = plans

    async def list(self, analysis_id):
        return self.plans


class MarketPriceServiceStub:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate_safely(self, plan):
        self.calls += 1
        return PriceAppropriatenessResult(
            status="unavailable",
            reason="refreshed",
        )


class InterpretationGeneratorStub:
    def __init__(self, property_id) -> None:
        self.property_id = property_id
        self.calls = 0

    async def generate(self, candidates):
        self.calls += 1
        return {
            str(self.property_id): AIInterpretation(
                summary=["갱신된 종합 해설"],
                strengths=AIInsightCard(title="장점", detail="상세"),
                burdens=AIInsightCard(title="부담", detail="상세"),
                things_to_check=AIInsightCard(
                    title="확인할 점",
                    detail="상세",
                ),
                evidence_count=3,
                suggested_questions=["왜 그런가요?"],
            ),
        }


def test_evaluate_returns_completed_evaluation_when_inputs_are_unchanged(
) -> None:
    analysis = Analysis(id=uuid4())
    evaluation = Evaluation(
        id=uuid4(),
        analysis_id=analysis.id,
        status="completed",
        progress=100,
        result={
            "result_version": 3,
            "analysis_id": str(analysis.id),
            "candidates": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    service = EvaluationService(
        AnalysisRepositoryStub(analysis),
        HousingPlanRepositorySpy(),
        EvaluationRepositoryStub(evaluation),
        MarketPriceServiceSpy(),
    )

    result = asyncio.run(service.evaluate(analysis.id))

    assert result is not None
    assert result.evaluation_id == evaluation.id
    assert result.status == "completed"
    assert result.progress == 100


def test_evaluate_refreshes_only_price_after_twenty_four_hours() -> None:
    analysis = Analysis(id=uuid4())
    plan = HousingPlan(id=uuid4(), analysis_id=analysis.id)
    evaluation = Evaluation(
        id=uuid4(),
        analysis_id=analysis.id,
        status="completed",
        progress=100,
        result={
            "result_version": 3,
            "analysis_id": str(analysis.id),
            "candidates": [
                {
                    "property_id": str(plan.id),
                    "financial_marker": "must-stay-unchanged",
                    "price_appropriateness": {"status": "available"},
                },
            ],
            "generated_at": (
                datetime.now(timezone.utc) - timedelta(hours=25)
            ).isoformat(),
        },
    )
    evaluation_repository = EvaluationRepositoryStub(evaluation)
    market_price_service = MarketPriceServiceStub()
    interpretation_generator = InterpretationGeneratorStub(plan.id)
    service = EvaluationService(
        AnalysisRepositoryStub(analysis),
        HousingPlanRepositoryStub([plan]),
        evaluation_repository,
        market_price_service,
        interpretation_generator,
    )

    result = asyncio.run(service.evaluate(analysis.id))

    assert result is not None
    assert result.evaluation_id == evaluation.id
    assert market_price_service.calls == 1
    assert interpretation_generator.calls == 1
    candidate = evaluation.result["candidates"][0]
    assert candidate["financial_marker"] == "must-stay-unchanged"
    assert candidate["price_appropriateness"]["reason"] == "refreshed"
    assert candidate["ai_interpretation"]["summary"] == [
        "갱신된 종합 해설",
    ]
