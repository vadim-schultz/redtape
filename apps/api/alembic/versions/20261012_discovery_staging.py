"""Add discovery staging tables, enums, and lineage events.

Revision ID: 20261012_discovery_staging
Revises: 20260929b_suggestion_event
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261012_discovery_staging"
down_revision: str | None = "20260929b_suggestion_event"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

discovery_source = postgresql.ENUM(
    "govdata", "pvog", "fim", "leika", "manual", name="discovery_source", create_type=True
)
discovery_task_status = postgresql.ENUM(
    "pending", "claimed", "completed", "failed", name="discovery_task_status", create_type=True
)
discovery_task_kind = postgresql.ENUM("fetch_url", "enrich_metadata", name="discovery_task_kind", create_type=True)
discovery_claim_kind = postgresql.ENUM(
    "new_document", "new_requirement", "metadata", name="discovery_claim_kind", create_type=True
)
discovery_event_type = postgresql.ENUM(
    "catalogue_upserted",
    "task_enqueued",
    "task_claimed",
    "fetch_logged",
    "claim_recorded",
    "emit_attempted",
    name="discovery_event_type",
    create_type=True,
)


def upgrade() -> None:
    op.create_table(
        "catalogue_service",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", discovery_source, nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("jurisdiction_id", sa.Uuid(), nullable=False),
        sa.Column("title_i18n", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=True),
        sa.Column("portal_url", sa.String(length=500), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("pipeline_stage", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "pipeline_stage IN ('T0', 'T1', 'T2', 'T3', 'T4')",
            name="ck_catalogue_service_pipeline_stage",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdiction.id"],
            name="fk_catalogue_service_jurisdiction_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalogue_service"),
        sa.UniqueConstraint("source", "external_id", name="uq_catalogue_service_source_external_id"),
    )
    op.create_index("ix_catalogue_service_jurisdiction_id", "catalogue_service", ["jurisdiction_id"], unique=False)

    op.create_table(
        "discovery_entity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_url", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalogue_service_id"],
            ["catalogue_service.id"],
            name="fk_discovery_entity_catalogue_service_id_catalogue_service",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_entity"),
        sa.UniqueConstraint("catalogue_service_id", "canonical_url", name="uq_discovery_entity_url"),
    )
    op.create_index(
        "ix_discovery_entity_catalogue_service_id", "discovery_entity", ["catalogue_service_id"], unique=False
    )

    op.create_table(
        "discovery_task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=False),
        sa.Column("kind", discovery_task_kind, nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("status", discovery_task_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_api_key_id", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalogue_service_id"],
            ["catalogue_service.id"],
            name="fk_discovery_task_catalogue_service_id_catalogue_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claimed_by_api_key_id"],
            ["api_key.id"],
            name="fk_discovery_task_claimed_by_api_key_id_api_key",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_task"),
    )
    op.create_index("ix_discovery_task_catalogue_service_id", "discovery_task", ["catalogue_service_id"], unique=False)
    op.create_index(
        "ix_discovery_task_status_priority_created_at",
        "discovery_task",
        ["status", "priority", "created_at"],
        unique=False,
    )

    op.create_table(
        "discovery_fetch_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("discovery_task_id", sa.Uuid(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("byte_length", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["discovery_task_id"],
            ["discovery_task.id"],
            name="fk_discovery_fetch_log_discovery_task_id_discovery_task",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_fetch_log"),
    )
    op.create_index(
        "ix_discovery_fetch_log_discovery_task_id", "discovery_fetch_log", ["discovery_task_id"], unique=False
    )

    op.create_table(
        "discovery_claim",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("discovery_entity_id", sa.Uuid(), nullable=False),
        sa.Column("kind", discovery_claim_kind, nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["discovery_entity_id"],
            ["discovery_entity.id"],
            name="fk_discovery_claim_discovery_entity_id_discovery_entity",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_claim"),
    )
    op.create_index("ix_discovery_claim_discovery_entity_id", "discovery_claim", ["discovery_entity_id"], unique=False)

    op.create_table(
        "discovery_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", discovery_event_type, nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=True),
        sa.Column("discovery_task_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalogue_service_id"],
            ["catalogue_service.id"],
            name="fk_discovery_event_catalogue_service_id_catalogue_service",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["discovery_task_id"],
            ["discovery_task.id"],
            name="fk_discovery_event_discovery_task_id_discovery_task",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_event"),
    )
    op.create_index(
        "ix_discovery_event_catalogue_created_at",
        "discovery_event",
        ["catalogue_service_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_discovery_event_catalogue_created_at", table_name="discovery_event")
    op.drop_table("discovery_event")
    op.drop_index("ix_discovery_claim_discovery_entity_id", table_name="discovery_claim")
    op.drop_table("discovery_claim")
    op.drop_index("ix_discovery_fetch_log_discovery_task_id", table_name="discovery_fetch_log")
    op.drop_table("discovery_fetch_log")
    op.drop_index("ix_discovery_task_status_priority_created_at", table_name="discovery_task")
    op.drop_index("ix_discovery_task_catalogue_service_id", table_name="discovery_task")
    op.drop_table("discovery_task")
    op.drop_index("ix_discovery_entity_catalogue_service_id", table_name="discovery_entity")
    op.drop_table("discovery_entity")
    op.drop_index("ix_catalogue_service_jurisdiction_id", table_name="catalogue_service")
    op.drop_table("catalogue_service")

    discovery_event_type.drop(op.get_bind(), checkfirst=True)
    discovery_claim_kind.drop(op.get_bind(), checkfirst=True)
    discovery_task_kind.drop(op.get_bind(), checkfirst=True)
    discovery_task_status.drop(op.get_bind(), checkfirst=True)
    discovery_source.drop(op.get_bind(), checkfirst=True)
