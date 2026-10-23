"""Add discovery_run for explicit worker-drain health.

Revision ID: 20261023_discovery_run
Revises: 20261015_claim_fingerprint
Create Date: 2026-10-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_discovery_run"
down_revision: str | None = "20261015_claim_fingerprint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'running'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("remaining_count", sa.Integer(), nullable=True),
        sa.Column("stop_reason", sa.String(length=32), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_run_status_finished_at", "discovery_run", ["status", "finished_at"])


def downgrade() -> None:
    op.drop_index("ix_discovery_run_status_finished_at", table_name="discovery_run")
    op.drop_table("discovery_run")
