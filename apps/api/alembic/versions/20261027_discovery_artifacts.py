"""Add discovery_artifact, task artifact and result note columns, and the render_page label.

Revision ID: 20261027_artifacts
Revises: 20261026_candidates
Create Date: 2026-10-27

Artifacts hold metadata only; bytes live in the object store. The same revision gives
``discovery_task`` its ``artifact_id`` and ``result_note``, adds the deferred foreign key on
``discovery_candidate_mention.artifact_id``, and extends two native enums: ``render_page`` on
``discovery_task_kind`` and ``task_released`` on ``discovery_event_type``. Postgres cannot remove
enum labels, so the downgrade leaves both labels in place (they are inert) and drops everything else.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261027_artifacts"
down_revision: str | None = "20261026_candidates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KIND_ENUM = postgresql.ENUM("html_snapshot", "screenshot", name="discovery_artifact_kind", create_type=False)
NEW_ENUM_LABELS: tuple[tuple[str, str], ...] = (
    ("discovery_task_kind", "render_page"),
    ("discovery_event_type", "task_released"),
)
TASK_FK = "fk_discovery_task_artifact_id"
MENTION_FK = "discovery_candidate_mention_artifact_id_fkey"


def _add_enum_labels() -> None:
    """Add the new labels outside a transaction, as ``ADD VALUE`` requires."""
    with op.get_context().autocommit_block():
        for type_name, label in NEW_ENUM_LABELS:
            op.execute(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{label}'")


def _create_artifact_table() -> None:
    op.create_table(
        "discovery_artifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=False),
        sa.Column("discovery_task_id", sa.Uuid(), nullable=True),
        sa.Column("kind", KIND_ENUM, nullable=False),
        sa.Column("storage_key", sa.String(length=300), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("final_url", sa.String(length=500), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["catalogue_service_id"], ["catalogue_service.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discovery_task_id"], ["discovery_task.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalogue_service_id", "kind", "sha256", name="uq_discovery_artifact_catalogue_kind_sha256"),
    )
    op.create_index("ix_discovery_artifact_catalogue_service_id", "discovery_artifact", ["catalogue_service_id"])


def _link_tasks_and_mentions() -> None:
    op.add_column("discovery_task", sa.Column("artifact_id", sa.Uuid(), nullable=True))
    op.add_column("discovery_task", sa.Column("result_note", sa.String(length=200), nullable=True))
    op.create_foreign_key(TASK_FK, "discovery_task", "discovery_artifact", ["artifact_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(
        MENTION_FK, "discovery_candidate_mention", "discovery_artifact", ["artifact_id"], ["id"], ondelete="SET NULL"
    )


def upgrade() -> None:
    _add_enum_labels()
    KIND_ENUM.create(op.get_bind(), checkfirst=True)
    _create_artifact_table()
    _link_tasks_and_mentions()


def downgrade() -> None:
    op.drop_constraint(MENTION_FK, "discovery_candidate_mention", type_="foreignkey")
    op.drop_constraint(TASK_FK, "discovery_task", type_="foreignkey")
    op.drop_column("discovery_task", "result_note")
    op.drop_column("discovery_task", "artifact_id")
    op.drop_table("discovery_artifact")
    KIND_ENUM.drop(op.get_bind(), checkfirst=True)
