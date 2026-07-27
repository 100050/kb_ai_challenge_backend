"""add housing comparison fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "housing_plans",
        sa.Column("property_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "housing_plans",
        sa.Column("legal_dong_code", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "housing_plans",
        sa.Column("exclusive_area_m2", sa.Float(), nullable=True),
    )
    op.create_index(
        op.f("ix_housing_plans_legal_dong_code"),
        "housing_plans",
        ["legal_dong_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_housing_plans_legal_dong_code"),
        table_name="housing_plans",
    )
    op.drop_column("housing_plans", "exclusive_area_m2")
    op.drop_column("housing_plans", "legal_dong_code")
    op.drop_column("housing_plans", "property_type")
