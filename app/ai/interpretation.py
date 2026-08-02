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
- summary는 핵심 결론과 이유가 자연스럽게 이어지는 2~4개의 문장으로
  작성합니다. 지표 이름과 숫자만 나열하지 않습니다.
- strengths의 title은 확인된 장점을 짧게 요약하고, detail은 그 장점이
  사용자에게 어떤 의미인지 근거 수치와 함께 1~2문장으로 설명합니다.
  충족된 항목이 없다면 장점을 억지로 만들지 말고 "확인된 재무적 강점
  없음"이라고 명시합니다.
- burdens는 가장 중요한 부담의 원인과 영향을 설명합니다. 음수 금액은
  "-87,090만 원"처럼 부호를 그대로 읽지 말고 "8억 7,090만 원 부족"처럼
  부족액의 의미가 드러나게 표현합니다.
- things_to_check는 사용자가 실제로 확인할 행동, 계산의 가정 또는 매물
  메모처럼 정량 지표에 반영되지 않은 사항을 설명합니다. 단순히
  "입주 후 유동자산 -87,090만 원을 확인하세요"처럼 계산값을 반복하지
  않습니다.
- "지표명 + 값 + 확인하세요" 형태의 기계적인 문장을 사용하지 않습니다.
- 초기자금이 부족한 경우 계약 체결을 가정한 이후 계산은 참고값이라는
  warnings를 우선 설명하고, 큰 음수 유동자산을 독립된 확인 사항처럼
  제시하지 않습니다.
- 원 단위 값은 의미가 바뀌지 않는 범위에서 만 원 또는 억 원 단위의
  자연스러운 한국어 금액으로 표현할 수 있습니다.
- 매물 메모는 사용자가 입력한 정보이므로 검증된 사실처럼 단정하지
  않습니다.
- 추천, 순위, 계약 확정 표현을 사용하지 않습니다.
- 각 입력 property_id를 빠짐없이 그대로 반환합니다.
""".strip()


class AIInterpretationGenerator:
    def __init__(self, agent: Agent[None, AIInterpretationBatch]) -> None:
        self.agent = agent

    async def generate(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, AIInterpretation]:
        result = await self.agent.run(
            "다음 매물별 분석 결과를 카드 구조로 작성하되, 각 카드 문장은 "
            "수치의 의미와 영향을 자연스럽게 설명하세요.\n"
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
