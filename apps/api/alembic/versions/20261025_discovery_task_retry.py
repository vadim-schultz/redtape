"""Add discovery_task.attempt_count and discovery_task.not_before.

Revision ID: 20261025_task_retry
Revises: 20261024_task_kinds
Create Date: 2026-10-25

``attempt_count`` counts leases; ``not_before`` holds a retried task back until
its backoff has elapsed. Both are dropped on downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_task_retry"
down_revision: str | None = "20261024_task_kinds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovery_task",
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("discovery_task", sa.Column("not_before", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_task", "not_before")
    op.drop_column("discovery_task", "attempt_count")
