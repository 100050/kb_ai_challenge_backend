from datetime import datetime, timezone
from uuid import UUID, uuid4

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.housing_plan import HousingPlan


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    # 하나의 주거 분석 작업을 식별하는 UUID
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # 분석의 처리 상태: 초안, 평가 중, 완료 또는 실패
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # 사용자가 다음으로 입력해야 하는 단계
    current_step: Mapped[str] = mapped_column(String(30), default="cash_flow")

    # 전체 입력 및 평가 과정의 진행률(0~100)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # 매월 반복적으로 확보할 수 있는 세후 현금유입
    after_tax_monthly_income: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 주거비와 교통비를 제외한 월 생활비
    monthly_living_expenses_excluding_housing_and_transport: Mapped[
        int | None
    ] = mapped_column(BigInteger, nullable=True)

    # 입주 이후에도 계속 납부하는 기존 대출의 월 원리금 상환액
    existing_loan_monthly_payment: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 매월 유지하려는 저축 및 투자 금액
    target_monthly_savings: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 예정 지출과 목표 저축 이후에도 남겨둘 월 완충 금액
    monthly_safety_margin: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 새 계약에 실제로 사용할 수 있는 현금성 자산
    available_cash: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 입주 후에도 보유하려는 최소 유동자산
    minimum_emergency_fund: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 향후 회수할 수 있는 기존 임차보증금
    recoverable_existing_rental_deposit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 기존 임차보증금을 새 계약일 전에 회수할 수 있는지 여부
    existing_rental_deposit_available_before_contract: Mapped[
        bool | None
    ] = mapped_column(Boolean, nullable=True)

    # 이 분석에 연결된 후보 매물과 매물별 대출 및 추가 비용
    housing_plans: Mapped[list["HousingPlan"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    conversation: Mapped["Conversation | None"] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

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
