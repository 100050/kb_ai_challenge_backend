import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.schemas.evaluation import AIInterpretation, AIInterpretationBatch


INTERPRETATION_INSTRUCTIONS = """
당신은 주거 후보의 가격 및 재무 분석 결과를 요약하는 한국어 상담
도우미입니다.

- 입력 JSON에 존재하는 수치와 상태만 사용하고 숫자를 새로 계산하거나
  추측하지 않습니다.
- strengths에는 충족한 재무 기준을, burdens에는 가격 또는 재무 부담을,
  things_to_check에는 매물 메모를 포함한 정성적 확인 사항을 작성합니다.
- 매물 메모는 사용자가 입력한 정보이므로 검증된 사실처럼 단정하지
  않습니다.
- 추천, 순위, 계약 확정 표현을 사용하지 않습니다.
- 각 입력 property_id를 빠짐없이 그대로 반환합니다.
- suggested_questions는 해당 매물 결과를 챗봇에 질문할 수 있는 짧은
  한국어 문장으로 작성합니다.
""".strip()


class AIInterpretationGenerator:
    def __init__(self, agent: Agent[None, AIInterpretationBatch]) -> None:
        self.agent = agent

    async def generate(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, AIInterpretation]:
        result = await self.agent.run(
            "다음 매물별 분석 결과를 화면용으로 구조화해 해설하세요.\n"
            + json.dumps(candidates, ensure_ascii=False, default=str),
        )
        return {
            str(item.property_id): item.interpretation
            for item in result.output.candidates
        }


def create_interpretation_generator(
    model: Model,
) -> AIInterpretationGenerator:
    agent = Agent(
        model,
        output_type=AIInterpretationBatch,
        instructions=INTERPRETATION_INSTRUCTIONS,
    )
    return AIInterpretationGenerator(agent)
