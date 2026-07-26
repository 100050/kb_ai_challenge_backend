"""remove duplicate evaluation unique constraint

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "evaluations_analysis_id_key",
        "evaluations",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "evaluations_analysis_id_key",
        "evaluations",
        ["analysis_id"],
    )
