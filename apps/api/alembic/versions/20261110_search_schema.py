"""Add the search schema: search text with full-text vectors, embeddings and the embedding task queue.

Revision ID: 20261110_search_schema
Revises: 20261105_retire_legacy_taxonomy
Create Date: 2026-11-10

Creates the ``vector`` and ``unaccent`` extensions (the migration fails loudly if either cannot be created; on Supabase
they must be enabled first), three tables keyed by candidate, their GIN and HNSW indexes, the partial unique index that
keeps one open embedding task per ``(candidate, model, locale)``, and the generic ``work_task_status`` enum.

``halfvec(1024)`` freezes the chapter 1 decision: the model's native width, stored in half precision. The downgrade
drops what this revision added and leaves the extensions installed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy.dialects import postgresql

revision: str = "20261110_search_schema"
down_revision: str | None = "20261105_retire_legacy_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

work_task_status = postgresql.ENUM("pending", "claimed", "completed", "failed", name="work_task_status", create_type=False)


def _candidate_id() -> sa.Column:
    """Return the candidate foreign key column shared by the three tables."""
    return sa.Column(
        "candidate_id",
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("discovery_document_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    work_task_status.create(op.get_bind(), checkfirst=True)
    _create_search_text()
    _create_embedding()
    _create_embedding_task()


def downgrade() -> None:
    op.drop_table("embedding_task")
    op.drop_table("candidate_embedding")
    op.drop_table("candidate_search_text")
    work_task_status.drop(op.get_bind(), checkfirst=True)


def _create_search_text() -> None:
    op.create_table(
        "candidate_search_text",
        _candidate_id(),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tsv_native", postgresql.TSVECTOR(), nullable=False),
        sa.Column("tsv_simple", postgresql.TSVECTOR(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("candidate_id", "locale"),
    )
    op.create_index("ix_candidate_search_text_tsv_native", "candidate_search_text", ["tsv_native"], postgresql_using="gin")
    op.create_index("ix_candidate_search_text_tsv_simple", "candidate_search_text", ["tsv_simple"], postgresql_using="gin")


def _create_embedding() -> None:
    op.create_table(
        "candidate_embedding",
        _candidate_id(),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("embedding", HALFVEC(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("candidate_id", "model", "locale"),
    )
    op.create_index(
        "ix_candidate_embedding_hnsw",
        "candidate_embedding",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "halfvec_cosine_ops"},
    )


def _create_embedding_task() -> None:
    op.create_table(
        "embedding_task",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _candidate_id(),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("status", work_task_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_api_key_id", sa.Uuid(as_uuid=True), sa.ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_embedding_task_open",
        "embedding_task",
        ["candidate_id", "model", "locale"],
        unique=True,
        postgresql_where=sa.text("status in ('pending', 'claimed')"),
    )
    op.create_index("ix_embedding_task_status_priority_created_at", "embedding_task", ["status", "priority", "created_at"])
