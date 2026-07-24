from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.analysis import utc_now

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class HousingPlan(Base):
    __tablename__ = "housing_plans"

    # 분석 내 후보 매물을 식별하는 서버 발급 UUID
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # 이 매물이 속한 분석의 UUID
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    housing_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    deposit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    monthly_rent: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    maintenance_fee: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    utilities: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transportation_cost: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 이 매물에만 적용되는 만기일시상환 보증금 대출 계획
    deposit_loan_amount: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    annual_interest_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # 이 매물 계약 및 입주에 필요한 일회성 추가 비용
    brokerage_fee: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    moving_cost: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    other_move_in_cost: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="housing_plans")

    @property
    def is_complete(self) -> bool:
        required_values = (
            self.name,
            self.address,
            self.housing_type,
            self.deposit,
            self.monthly_rent,
            self.maintenance_fee,
            self.utilities,
            self.transportation_cost,
            self.deposit_loan_amount,
            self.annual_interest_rate,
            self.brokerage_fee,
            self.moving_cost,
            self.other_move_in_cost,
        )
        if any(value is None for value in required_values):
            return False
        if self.housing_type not in {"jeonse", "monthly_rent"}:
            return False
        return self.housing_type != "jeonse" or self.monthly_rent == 0
