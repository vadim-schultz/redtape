"""Seed and backfill the canonical category projection from frozen local data.

Revision ID: 20261104_category_backfill
Revises: 20261104_category_schema
Create Date: 2026-11-04

The operation reads only the existing database and checked-in category contract.
It never calls PVOG or an LLM. Legacy tables and links are retained. The downgrade
is intentionally a no-op because this is a forward-only data projection; downgrading
the preceding expand revision remains the rollback boundary for the additive schema.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.orm import Session

from scripts.category_backfill import run_category_backfill

revision: str = "20261104_category_backfill"
down_revision: str | None = "20261104_category_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Run the deterministic canonical seed and legacy crosswalk projection."""
    with Session(bind=op.get_bind(), autoflush=False) as session:
        run_category_backfill(session)


def downgrade() -> None:
    """Keep projected data until the preceding schema revision is downgraded."""
    pass
