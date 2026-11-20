"""Add discovery_fetch_log.body_sha256: the sha256 of each fetched body, for change detection.

Revision ID: 20261119_fetch_body_sha256
Revises: 20261119_task_failure_class
Create Date: 2026-11-19

The column is nullable and starts empty. A row written before this revision keeps it null and is never compared, so the
first body fetched after the deploy counts as changed. The downgrade drops the column only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_fetch_body_sha256"
down_revision: str | None = "20261119_task_failure_class"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("discovery_fetch_log", sa.Column("body_sha256", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_fetch_log", "body_sha256")
