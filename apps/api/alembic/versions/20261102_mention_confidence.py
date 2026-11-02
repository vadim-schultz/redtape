"""Add the two direct-confidence columns to discovery_candidate_mention.

Revision ID: 20261102_mention_confidence
Revises: 20261029_staging_edges
Create Date: 2026-11-02

Additive and behaviourally a no-op: every existing mention stays ``NULL`` on both columns, which the
scoring engine (situation-tag-hierarchy chapter 1) reads as "score this mention's assertion via the
LLM-evidence curve" — the same as before this migration. A non-``NULL`` value, populated later by chapter
3 for PVOG mentions, means the mention supplies its own fixed confidence directly.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_mention_confidence"
down_revision: str | None = "20261029_staging_edges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MENTION_TABLE = "discovery_candidate_mention"
COLUMNS = ("direct_domain_confidence", "direct_situation_confidence")


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column(MENTION_TABLE, sa.Column(column, sa.Float(), nullable=True))


def downgrade() -> None:
    for column in COLUMNS:
        op.drop_column(MENTION_TABLE, column)
