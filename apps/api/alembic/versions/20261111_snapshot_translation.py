"""Add the snapshot translation schema: the index of translated procedure pages and their task queue.

Revision ID: 20261111_snapshot_translation
Revises: 20261111_translation_schema
Create Date: 2026-11-12

``snapshot_translation`` holds one row per (catalogue row, locale): the artifact sha it was made from, the cleaned-text
hash and the object key, or the reason the page was skipped. ``snapshot_translation_task`` mirrors ``translation_task``
but is keyed by the catalogue row, and its artifact columns stay empty until a claim fills them. Both tables reuse the
``work_task_status`` enum, which this revision neither creates nor drops. The downgrade drops the two tables only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_snapshot_translation"
down_revision: str | None = "20261111_translation_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

work_task_status = postgresql.ENUM(
    "pending", "claimed", "completed", "failed", name="work_task_status", create_type=False
)
CK_STORAGE_XOR_SKIP = "ck_snapshot_translation_storage_xor_skip"


def _catalogue_id() -> sa.Column:
    """Return the catalogue row foreign key column shared by both tables."""
    return sa.Column(
        "catalogue_service_id",
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("catalogue_service.id", ondelete="CASCADE"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column]:
    """Return the ``created_at`` and ``updated_at`` columns."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    _create_snapshot_translation()
    _create_snapshot_translation_task()


def downgrade() -> None:
    op.drop_table("snapshot_translation_task")
    op.drop_table("snapshot_translation")


def _create_snapshot_translation() -> None:
    op.create_table(
        "snapshot_translation",
        _catalogue_id(),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=True),
        sa.Column("engine", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("skipped_reason", sa.String(40), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("catalogue_service_id", "locale"),
        sa.CheckConstraint("storage_key IS NULL OR skipped_reason IS NULL", name=CK_STORAGE_XOR_SKIP),
    )


def _create_snapshot_translation_task() -> None:
    op.create_table(
        "snapshot_translation_task",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _catalogue_id(),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("artifact_id", sa.Uuid(as_uuid=True), sa.ForeignKey("discovery_artifact.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=True),
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
        "uq_snapshot_translation_task_open",
        "snapshot_translation_task",
        ["catalogue_service_id", "locale"],
        unique=True,
        postgresql_where=sa.text("status in ('pending', 'claimed')"),
    )
    op.create_index(
        "ix_snapshot_translation_task_status_priority_created_at",
        "snapshot_translation_task",
        ["status", "priority", "created_at"],
    )
