"""Add discovery_document_candidate and discovery_candidate_mention.

Revision ID: 20261026_candidates
Revises: 20261025_task_retry
Create Date: 2026-10-26

Candidates deduplicate document nodes per jurisdiction; mentions keep the
provenance and the procedure-to-document relation. ``suggestion_id`` and
``artifact_id`` carry no foreign key yet (the suggestion table belongs to another
feature; artifacts arrive in a later revision). Downgrade drops both tables and
both enum types.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261026_candidates"
down_revision: str | None = "20261025_task_retry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_ENUM = postgresql.ENUM("staged", "emitted", name="discovery_candidate_status", create_type=False)
ROLE_ENUM = postgresql.ENUM("required", "form", name="discovery_mention_role", create_type=False)


def _create_candidate_table() -> None:
    op.create_table(
        "discovery_document_candidate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("jurisdiction_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("title_i18n", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("official_url", sa.String(length=500), nullable=True),
        sa.Column("status", STATUS_ENUM, server_default=sa.text("'staged'"), nullable=False),
        sa.Column("suggestion_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["jurisdiction_id"], ["jurisdiction.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jurisdiction_id", "key", name="uq_discovery_candidate_jurisdiction_key"),
    )
    op.create_index(
        "ix_discovery_document_candidate_jurisdiction_id", "discovery_document_candidate", ["jurisdiction_id"]
    )


def _create_mention_table() -> None:
    op.create_table(
        "discovery_candidate_mention",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=False),
        sa.Column("role", ROLE_ENUM, nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_field", sa.String(length=200), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("extractor", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["discovery_document_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catalogue_service_id"], ["catalogue_service.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id", "catalogue_service_id", "role", "source_field", name="uq_discovery_candidate_mention_key"
        ),
    )
    op.create_index("ix_discovery_candidate_mention_candidate_id", "discovery_candidate_mention", ["candidate_id"])
    op.create_index(
        "ix_discovery_candidate_mention_catalogue_service_id", "discovery_candidate_mention", ["catalogue_service_id"]
    )


def upgrade() -> None:
    STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    ROLE_ENUM.create(op.get_bind(), checkfirst=True)
    _create_candidate_table()
    _create_mention_table()


def downgrade() -> None:
    op.drop_table("discovery_candidate_mention")
    op.drop_table("discovery_document_candidate")
    ROLE_ENUM.drop(op.get_bind(), checkfirst=True)
    STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
