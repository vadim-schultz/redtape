"""Retire the legacy domain, life-situation and group taxonomy in favour of canonical categories.

Revision ID: 20261105_retire_legacy_taxonomy
Revises: 20261104_category_backfill
Create Date: 2026-11-05

Forward-only at the data level. Every step runs in the migration transaction, so an abort rolls back all of it:

1. Lock the retired relations exclusively, then archive each into ``legacy_taxonomy_archive`` and record its row count
   and checksum. The lock stops a concurrent write from landing between the copy and the drop.
2. Verify that each archive copy equals its source by row count and checksum. Any mismatch aborts.
3. Add the canonical mention columns and project the legacy mention axis values into them through the frozen crosswalk.
4. Replay the category backfill and log its full report. Any unmapped, ambiguous or conflict row aborts.
5. Drop the legacy mention axis columns and the retired term and link tables.

The downgrade recreates the legacy schema empty and restores the mention columns as empty. It does not restore
data: the archive schema is the recovery source, and it is never dropped by this revision.
"""

import json
import logging
from collections.abc import Sequence
from dataclasses import asdict

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Column, Connection
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from scripts.category_backfill import BackfillReport, run_category_backfill
from scripts.category_mention_projection import project_mention_categories
from scripts.legacy_taxonomy_archive import (
    MENTION_TABLE,
    RETIRED_TABLES,
    ArchiveMismatchError,
    archive_legacy_taxonomy,
    compare_archive,
)

revision: str = "20261105_retire_legacy_taxonomy"
down_revision: str | None = "20261104_category_backfill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOGGER = logging.getLogger("alembic.retire_legacy_taxonomy")
CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
LEGACY_MENTION_COLUMNS = ("domain_codes", "situation_codes", "direct_domain_confidence", "direct_situation_confidence")


class BackfillGateError(RuntimeError):
    """Raised when the backfill replay leaves unmapped, ambiguous or conflict legacy rows."""


def upgrade() -> None:
    """Archive, verify, project, replay behind the backfill gate, then drop the legacy taxonomy."""
    bind = op.get_bind()
    archive_legacy_taxonomy(bind)
    _verify_archive(bind)
    _project_mention_categories(bind)
    _gate_backfill(_replay_backfill(bind))
    _drop_legacy_taxonomy()


def downgrade() -> None:
    """Recreate the empty legacy schema; the archive schema holds the only copy of the retired rows."""
    _recreate_term_tables()
    _recreate_link_tables()
    op.add_column(MENTION_TABLE, sa.Column("domain_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("situation_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("direct_domain_confidence", sa.Float(), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("direct_situation_confidence", sa.Float(), nullable=True))
    op.drop_column(MENTION_TABLE, "direct_category_confidence")
    op.drop_column(MENTION_TABLE, "category_codes")


def _verify_archive(bind: Connection) -> None:
    """Abort unless every archive copy matches its source by row count and checksum."""
    mismatches = [check for check in compare_archive(bind) if not check.matches]
    if mismatches:
        raise ArchiveMismatchError(mismatches)


def _project_mention_categories(bind: Connection) -> None:
    """Add the canonical mention columns and fill them from the legacy mention axis values."""
    op.add_column(MENTION_TABLE, sa.Column("category_codes", postgresql.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("direct_category_confidence", sa.Float(), nullable=True))
    project_mention_categories(bind)


def _replay_backfill(bind: Connection) -> BackfillReport:
    """Replay the category backfill inside the migration transaction and log its full report."""
    with Session(bind=bind, autoflush=False) as session:
        report = run_category_backfill(session)
    LOGGER.info("legacy taxonomy backfill report: %s", json.dumps(asdict(report), default=str, sort_keys=True))
    return report


def _gate_backfill(report: BackfillReport) -> None:
    """Abort unless the replay has no unmapped, ambiguous or conflict legacy rows."""
    failing = _failing_counts(report)
    if failing:
        raise BackfillGateError(f"legacy backfill blocked by {', '.join(failing)}; see the logged report")


def _failing_counts(report: BackfillReport) -> list[str]:
    """Name each blocking bucket that holds rows, as ``bucket=count``."""
    blocking = {
        "unmapped": report.unmapped_rows,
        "ambiguous": report.ambiguous_rows,
        "conflict": report.conflict_rows,
    }
    return [f"{name}={count}" for name, count in blocking.items() if count]


def _drop_legacy_taxonomy() -> None:
    """Drop the legacy mention columns, then the retired tables, children before parents."""
    for column in LEGACY_MENTION_COLUMNS:
        op.drop_column(MENTION_TABLE, column)
    for table in reversed(RETIRED_TABLES):
        op.drop_table(table)


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
        sa.Column(
            "document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("domain_id", sa.Uuid(as_uuid=True), sa.ForeignKey("domain.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
    )
    op.create_table(
        "document_life_situation",
        sa.Column(
            "document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "life_situation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("life_situation.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("pvog_leaf_code", sa.String(length=64), nullable=True),
    )
