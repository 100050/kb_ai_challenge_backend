"""add existing deposit availability

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column(
            "existing_rental_deposit_available_before_contract",
            sa.Boolean(),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE analyses "
        "SET existing_rental_deposit_available_before_contract = true",
    )


def downgrade() -> None:
    op.drop_column(
        "analyses",
        "existing_rental_deposit_available_before_contract",
    )
