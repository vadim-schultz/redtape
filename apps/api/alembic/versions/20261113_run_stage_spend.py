"""Add discovery_run.stage and discovery_run.spend: each drain run names its stage and what it spent.

Revision ID: 20261113_run_stage_spend
Revises: 20261112_locale_machine_flag
Create Date: 2026-11-13

Existing rows were all written by the worker drain, so ``stage`` takes ``worker_drain`` for them through the server
default. ``spend`` is empty for every existing row. The downgrade drops both columns only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261113_run_stage_spend"
down_revision: str | None = "20261112_locale_machine_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovery_run",
        sa.Column("stage", sa.String(length=32), nullable=True, server_default=sa.text("'worker_drain'")),
    )
    op.add_column("discovery_run", sa.Column("spend", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_run", "spend")
    op.drop_column("discovery_run", "stage")
