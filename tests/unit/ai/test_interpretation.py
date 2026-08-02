from app.ai.interpretation import INTERPRETATION_INSTRUCTIONS


def test_interpretation_prompt_requires_natural_deficit_explanation() -> None:
    assert "지표명 + 값 + 확인하세요" in INTERPRETATION_INSTRUCTIONS
    assert "부족액의 의미" in INTERPRETATION_INSTRUCTIONS
    assert "warnings를 우선 설명" in INTERPRETATION_INSTRUCTIONS

