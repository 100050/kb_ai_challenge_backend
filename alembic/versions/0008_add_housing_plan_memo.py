"""add housing plan memo

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "housing_plans",
        sa.Column("memo", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("housing_plans", "memo")
