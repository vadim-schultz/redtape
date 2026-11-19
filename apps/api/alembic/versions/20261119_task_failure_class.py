"""Add discovery_task.failure_class and discovery_task.text_hash: why a task failed, and the cleaned-text hash of an extraction.

Revision ID: 20261119_task_failure_class
Revises: 20261113_run_stage_spend
Create Date: 2026-11-19

Both columns are nullable and start empty, so every existing row reads as an unclassified failure (permanent for the
requeue) and as an extraction with no recorded text hash. ``failure_class`` is a ``String(32)``; the API validates the
values, so a later class needs no migration. The downgrade drops both columns only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_task_failure_class"
down_revision: str | None = "20261113_run_stage_spend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("discovery_task", sa.Column("failure_class", sa.String(length=32), nullable=True))
    op.add_column("discovery_task", sa.Column("text_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_task", "text_hash")
    op.drop_column("discovery_task", "failure_class")
