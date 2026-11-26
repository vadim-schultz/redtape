"""Create fair_selection_state table and add phase column to task tables.

Revision ID: 20261120_fair_selection_state
Revises: 20261119_fetch_body_sha256
Create Date: 2026-11-20

This migration creates the fair_selection_state table which tracks the phase of each
entity (candidate or catalogue_service) in each pipeline. It also adds the phase column
to task tables to record which phase each task belongs to, defaulting to phase 1.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_fair_selection_state"
down_revision: str | None = "20261119_fetch_body_sha256"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TASK_TABLES = ("translation_task", "snapshot_translation_task", "embedding_task", "discovery_task")
# (pipeline, task table, column holding the entity id) for each pipeline that tracks entities.
_BACKFILL_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("translation", "translation_task", "candidate_id"),
    ("snapshot_translation", "snapshot_translation_task", "catalogue_service_id"),
    ("embedding", "embedding_task", "candidate_id"),
    ("discovery", "discovery_task", "catalogue_service_id"),
)


def upgrade() -> None:
    """Create fair_selection_state table and add phase columns to task tables."""
    _create_fair_selection_state_table()
    _add_phase_to_task_tables()
    _backfill_fair_selection_state()


def downgrade() -> None:
    """Drop fair_selection_state table and remove phase columns from task tables."""
    _remove_phase_from_task_tables()
    _drop_fair_selection_state_table()


def _create_fair_selection_state_table() -> None:
    """Create the fair_selection_state table with indices."""
    op.create_table(
        "fair_selection_state",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("pipeline", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("coverage_bitmap", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Unique constraint on (pipeline, entity_id) pair
    op.create_unique_constraint(
        "uq_fair_selection_state_entity",
        "fair_selection_state",
        ["pipeline", "entity_id"],
    )

    # Index for efficient lookup by pipeline and entity_id
    op.create_index(
        "ix_fair_selection_state_pipeline_entity",
        "fair_selection_state",
        ["pipeline", "entity_id"],
    )


def _drop_fair_selection_state_table() -> None:
    """Drop the fair_selection_state table."""
    op.drop_table("fair_selection_state")


def _add_phase_to_task_tables() -> None:
    """Add phase column to all task tables."""
    for table_name in _TASK_TABLES:
        op.add_column(
            table_name,
            sa.Column("phase", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )


def _remove_phase_from_task_tables() -> None:
    """Remove phase column from all task tables."""
    for table_name in _TASK_TABLES:
        op.drop_column(table_name, "phase")


def _backfill_fair_selection_state() -> None:
    """Backfill fair_selection_state with existing entities from task tables.

    Creates one state row per unique entity per pipeline, all with phase=1 and
    coverage_bitmap=0. This is idempotent: re-running does not create duplicates.
    """
    for pipeline, task_table, entity_column in _BACKFILL_SOURCES:
        _backfill_pipeline(pipeline, task_table, entity_column)


def _backfill_pipeline(pipeline: str, task_table: str, entity_column: str) -> None:
    """Insert one state row per distinct entity of ``task_table``; rows that already exist are skipped."""
    op.execute(
        sa.text(
            f"""
            INSERT INTO fair_selection_state (id, pipeline, entity_id, phase, coverage_bitmap)
            SELECT gen_random_uuid(), :pipeline, entity_id, 1, 0
            FROM (SELECT DISTINCT {entity_column} AS entity_id FROM {task_table}) AS entities
            ON CONFLICT (pipeline, entity_id) DO NOTHING
            """
        ).bindparams(pipeline=pipeline)
    )
