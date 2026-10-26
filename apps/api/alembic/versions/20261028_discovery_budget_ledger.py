"""Add discovery_budget_ledger, the shared usage counter for free allocations.

Revision ID: 20261028_budget_ledger
Revises: 20261027_artifacts
Create Date: 2026-10-28

One row per ``(period, resource)``; ``period`` is a UTC day (``YYYY-MM-DD``) or month (``YYYY-MM``)
chosen by the server. The table is additive and enum-free, so the downgrade only drops it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_budget_ledger"
down_revision: str | None = "20261027_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_budget_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False),
        sa.Column("resource", sa.String(length=40), nullable=False),
        sa.Column("used", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("exhausted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period", "resource", name="uq_discovery_budget_ledger_period_resource"),
    )


def downgrade() -> None:
    op.drop_table("discovery_budget_ledger")
