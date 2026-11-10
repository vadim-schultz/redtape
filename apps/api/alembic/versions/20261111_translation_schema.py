"""Add the translation schema: the index of stored translations and the translation task queue.

Revision ID: 20261111_translation_schema
Revises: 20261110_search_schema
Create Date: 2026-11-11

``candidate_translation`` holds no text: the translated title and description are objects in the object store
(decision D17) and this row records their key, content hash, provenance and the German source hash they answer.
``translation_task`` mirrors ``embedding_task`` and reuses chapter 3's ``work_task_status`` enum, which this
revision neither creates nor drops. The downgrade drops the two tables and the ``translation_source`` enum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_translation_schema"
down_revision: str | None = "20261110_search_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

work_task_status = postgresql.ENUM("pending", "claimed", "completed", "failed", name="work_task_status", create_type=False)
translation_source = postgresql.ENUM("mt", "human", name="translation_source", create_type=False)


def _candidate_id() -> sa.Column:
    """Return the candidate foreign key column shared by both tables."""
    return sa.Column(
        "candidate_id",
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("discovery_document_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column]:
    """Return the ``created_at`` and ``updated_at`` columns."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    translation_source.create(op.get_bind(), checkfirst=True)
    _create_candidate_translation()
    _create_translation_task()


def downgrade() -> None:
    op.drop_table("translation_task")
    op.drop_table("candidate_translation")
    translation_source.drop(op.get_bind(), checkfirst=True)


def _create_candidate_translation() -> None:
    op.create_table(
        "candidate_translation",
        _candidate_id(),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source", translation_source, nullable=False, server_default=sa.text("'mt'")),
        sa.Column("engine", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("candidate_id", "locale"),
    )


def _create_translation_task() -> None:
    op.create_table(
        "translation_task",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _candidate_id(),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("status", work_task_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_api_key_id", sa.Uuid(as_uuid=True), sa.ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "uq_translation_task_open",
        "translation_task",
        ["candidate_id", "locale"],
        unique=True,
        postgresql_where=sa.text("status in ('pending', 'claimed')"),
    )
    op.create_index("ix_translation_task_status_priority_created_at", "translation_task", ["status", "priority", "created_at"])
