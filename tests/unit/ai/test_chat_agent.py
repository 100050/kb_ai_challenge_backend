import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from pydantic_ai.models.test import TestModel

from app.ai.agent import (
    AGENT_INSTRUCTIONS,
    PROMPT_PATH,
    _regenerate_evaluation,
    create_chat_agent,
)
from app.schemas.evaluation import EvaluationStarted, FinancialEvaluationResult


def test_all_input_update_tools_execute_without_user_approval() -> None:
    agent = create_chat_agent(TestModel())

    tools = agent._function_toolset.tools

    assert set(tools) == {
        "get_calculation_formula",
        "get_calculation_breakdown",
        "update_cash_flow",
        "update_financial_goals",
        "update_housing_plan",
    }
    assert all(not tool.requires_approval for tool in tools.values())


def test_agent_uses_external_prompt_file() -> None:
    assert AGENT_INSTRUCTIONS == PROMPT_PATH.read_text(
        encoding="utf-8",
    ).strip()
    assert "<role>" in AGENT_INSTRUCTIONS
    assert "<data_rules>" in AGENT_INSTRUCTIONS
    assert "Respond in Korean." in AGENT_INSTRUCTIONS


class EvaluationServiceStub:
    def __init__(self) -> None:
        self.evaluation_id = uuid4()
        self.calls = 0

    async def evaluate(self, analysis_id):
        self.calls += 1
        return EvaluationStarted(
            evaluation_id=self.evaluation_id,
            status="completed",
            progress=100,
        )

    async def get_result(self, analysis_id):
        return FinancialEvaluationResult(
            analysis_id=analysis_id,
            candidates=[],
            generated_at=datetime.now(timezone.utc),
        )


def test_input_update_regenerates_evaluation() -> None:
    evaluation_service = EvaluationServiceStub()
    ctx = SimpleNamespace(
        deps=SimpleNamespace(
            analysis_id=uuid4(),
            evaluation_service=evaluation_service,
        ),
    )

    result = asyncio.run(_regenerate_evaluation(ctx))

    assert evaluation_service.calls == 1
    assert result == {
        "evaluation_regenerated": True,
        "evaluation_id": str(evaluation_service.evaluation_id),
        "evaluation_status": "completed",
        "evaluation_progress": 100,
        "evaluation_result": {
            "result_version": 8,
            "analysis_id": str(ctx.deps.analysis_id),
            "candidates": [],
            "generated_at": result["evaluation_result"]["generated_at"],
        },
    }
