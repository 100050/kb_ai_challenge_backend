from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID = Field(
        description="주거 분석 작업을 식별하는 UUID",
    )
    status: Literal["draft", "evaluating", "completed", "failed"] = Field(
        description="분석의 처리 상태",
    )
    current_step: str = Field(
        description="사용자가 다음으로 입력해야 하는 단계",
    )
    progress: int = Field(
        description="전체 입력 및 평가 과정의 진행률(0~100)",
    )
    created_at: datetime = Field(
        description="분석 작업이 최초 생성된 UTC 시각",
    )


class AnalysisDetail(AnalysisSummary):
    properties: list[dict[str, Any]] | None = Field(
        description="사용자가 비교할 후보 매물 목록. 입력 전에는 null",
    )
    cash_flow: dict[str, Any] | None = Field(
        description="월 소득, 생활비, 부채 상환액 등 현금 흐름. 입력 전에는 null",
    )
    financial_goals: dict[str, Any] | None = Field(
        description="현재 자산, 저축 목표 등 재무 목표. 입력 전에는 null",
    )
    loan_plan: dict[str, Any] | None = Field(
        description="대출 금액, 금리, 기간 등 대출 계획. 입력 전에는 null",
    )
    updated_at: datetime = Field(
        description="분석 작업이나 입력값이 마지막으로 변경된 UTC 시각",
    )
