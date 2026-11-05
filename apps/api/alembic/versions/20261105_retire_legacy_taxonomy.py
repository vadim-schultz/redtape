"""Retire the legacy domain, life-situation and group taxonomy in favour of canonical categories.

Revision ID: 20261105_retire_legacy_taxonomy
Revises: 20261104_category_backfill
Create Date: 2026-11-05

Forward-only at the data level, in this order:

1. Archive every legacy table and the legacy mention axis columns into ``legacy_taxonomy_archive`` with row-count
   evidence (``retirement_evidence``). Each archive copy is created once and never overwritten by a replay.
2. Add ``category_codes`` and ``direct_category_confidence`` to mentions and project the legacy axis values into
   them through the frozen crosswalk.
3. Replay the category backfill so legacy document links and PVOG leaf facts that appeared after the C2
   projection still reach ``document_category`` and ``document_external_classification`` before the drop.
4. Drop the legacy mention axis columns and the legacy term and link tables.

The downgrade recreates the legacy schema empty and restores the mention columns as empty. It does not restore
data: the archive schema is the recovery source, and it is never dropped by this revision.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from scripts.category_backfill import run_category_backfill
from scripts.category_mention_projection import project_mention_categories
from scripts.legacy_taxonomy_archive import archive_legacy_taxonomy

revision: str = "20261105_retire_legacy_taxonomy"
down_revision: str | None = "20261104_category_backfill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MENTION = "discovery_candidate_mention"
CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
LEGACY_MENTION_COLUMNS = ("domain_codes", "situation_codes", "direct_domain_confidence", "direct_situation_confidence")


def upgrade() -> None:
    """Archive, project, backfill, then drop the legacy taxonomy."""
    bind = op.get_bind()
    archive_legacy_taxonomy(bind)
    op.add_column(MENTION, sa.Column("category_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION, sa.Column("direct_category_confidence", sa.Float(), nullable=True))
    project_mention_categories(bind)
    with Session(bind=bind, autoflush=False) as session:
        run_category_backfill(session)
    for column in LEGACY_MENTION_COLUMNS:
        op.drop_column(MENTION, column)
    op.drop_table("document_life_situation")
    op.drop_table("document_domain")
    op.drop_table("life_situation")
    op.drop_table("life_situation_group")
    op.drop_table("domain")


def downgrade() -> None:
    """Recreate the empty legacy schema; the archive schema holds the only copy of the retired rows."""
    _recreate_term_tables()
    _recreate_link_tables()
    op.add_column(MENTION, sa.Column("domain_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION, sa.Column("situation_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION, sa.Column("direct_domain_confidence", sa.Float(), nullable=True))
    op.add_column(MENTION, sa.Column("direct_situation_confidence", sa.Float(), nullable=True))
    op.drop_column(MENTION, "direct_category_confidence")
    op.drop_column(MENTION, "category_codes")


def _term_columns() -> tuple[Column, ...]:
    return (
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def _recreate_term_tables() -> None:
    op.create_table(
        "domain",
        *_term_columns(),
        sa.UniqueConstraint("code", name="uq_domain_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_domain_code_kebab"),
    )
    op.create_table(
        "life_situation_group",
        *_term_columns(),
        sa.UniqueConstraint("code", name="uq_life_situation_group_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_life_situation_group_code_kebab"),
    )
    op.create_table(
        "life_situation",
        *_term_columns(),
        sa.Column("group_id", sa.Uuid(as_uuid=True), sa.ForeignKey("life_situation_group.id"), nullable=True),
        sa.UniqueConstraint("code", name="uq_life_situation_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_life_situation_code_kebab"),
    )


def _recreate_link_tables() -> None:
    op.create_table(
        "document_domain",
        sa.Column("document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("domain_id", sa.Uuid(as_uuid=True), sa.ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
    )
    op.create_table(
        "document_life_situation",
        sa.Column("document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "life_situation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("life_situation.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("pvog_leaf_code", sa.String(length=64), nullable=True),
    )
