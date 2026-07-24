"""add analysis inputs and housing plans

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("after_tax_monthly_income", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column(
            "monthly_living_expenses_excluding_housing_and_transport",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "analyses",
        sa.Column(
            "existing_loan_monthly_payment",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "analyses",
        sa.Column("target_monthly_savings", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("monthly_safety_margin", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("available_cash", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("minimum_emergency_fund", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column(
            "recoverable_existing_rental_deposit",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE analyses "
        "SET current_step = 'cash_flow', progress = 0 "
        "WHERE current_step = 'properties'",
    )

    op.create_table(
        "housing_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("housing_type", sa.String(length=20), nullable=True),
        sa.Column("deposit", sa.BigInteger(), nullable=True),
        sa.Column("monthly_rent", sa.BigInteger(), nullable=True),
        sa.Column("maintenance_fee", sa.BigInteger(), nullable=True),
        sa.Column("utilities", sa.BigInteger(), nullable=True),
        sa.Column("transportation_cost", sa.BigInteger(), nullable=True),
        sa.Column("deposit_loan_amount", sa.BigInteger(), nullable=True),
        sa.Column("annual_interest_rate", sa.Float(), nullable=True),
        sa.Column("brokerage_fee", sa.BigInteger(), nullable=True),
        sa.Column("moving_cost", sa.BigInteger(), nullable=True),
        sa.Column("other_move_in_cost", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_housing_plans_analysis_id"),
        "housing_plans",
        ["analysis_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_housing_plans_analysis_id"),
        table_name="housing_plans",
    )
    op.drop_table("housing_plans")

    op.drop_column("analyses", "recoverable_existing_rental_deposit")
    op.drop_column("analyses", "minimum_emergency_fund")
    op.drop_column("analyses", "available_cash")
    op.drop_column("analyses", "monthly_safety_margin")
    op.drop_column("analyses", "target_monthly_savings")
    op.drop_column("analyses", "existing_loan_monthly_payment")
    op.drop_column(
        "analyses",
        "monthly_living_expenses_excluding_housing_and_transport",
    )
    op.drop_column("analyses", "after_tax_monthly_income")
