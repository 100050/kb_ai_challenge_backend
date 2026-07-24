from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    # 하나의 주거 분석 작업을 식별하는 UUID
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # 분석의 처리 상태: 초안, 평가 중, 완료 또는 실패
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # 사용자가 다음으로 입력해야 하는 단계
    current_step: Mapped[str] = mapped_column(String(30), default="properties")

    # 전체 입력 및 평가 과정의 진행률(0~100)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # 분석 작업이 최초 생성된 UTC 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    # 분석 작업이나 입력값이 마지막으로 변경된 UTC 시각
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
