"""Add the confidence column to document_domain and document_life_situation.

Revision ID: 20261102_link_table_confidence
Revises: 20261102_mention_confidence
Create Date: 2026-11-02

``confidence`` freezes the scoring engine's (chapter 1 part A) continuous score onto a document's tag
at promotion time, so it survives for a later chapter's UI to sort and style by. The ``server_default``
backfills every row written before this migration to ``1.0`` (decision D7): there is no mention-level
data left to recompute a real score for an already-promoted document, so treating existing rows as fully
confident is the honest default, not a retroactive scoring attempt.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_link_table_confidence"
down_revision: str | None = "20261102_mention_confidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINK_TABLES = ("document_domain", "document_life_situation")


def upgrade() -> None:
    for table in LINK_TABLES:
        op.add_column(table, sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")))


def downgrade() -> None:
    for table in LINK_TABLES:
        op.drop_column(table, "confidence")
