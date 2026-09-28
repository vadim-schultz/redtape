"""Add suggestion table, enums and constraints.

Revision ID: 20260928_suggestion
Revises: 20260927c_api_key
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_suggestion"
down_revision: Union[str, None] = "20260927c_api_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

suggestion_kind = postgresql.ENUM("new_document", "new_requirement", name="suggestion_kind", create_type=True)
suggestion_status = postgresql.ENUM("pending", "approved", "rejected", name="suggestion_status", create_type=True)
suggestion_source = postgresql.ENUM("human", "crawler", name="suggestion_source", create_type=True)


def upgrade() -> None:
    op.create_table(
        "suggestion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", suggestion_kind, nullable=False),
        sa.Column("status", suggestion_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("source_type", suggestion_source, nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_by_api_key_id", sa.Uuid(), nullable=True),
        sa.Column("jurisdiction_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("normalized_url", sa.String(length=500), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_suggestion"),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["app_user.id"],
            name="fk_suggestion_submitted_by_user_id_app_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_api_key_id"],
            ["api_key.id"],
            name="fk_suggestion_submitted_by_api_key_id_api_key",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdiction.id"],
            name="fk_suggestion_jurisdiction_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(source_type = 'human' AND submitted_by_api_key_id IS NULL) "
            "OR (source_type = 'crawler' AND submitted_by_user_id IS NULL)",
            name="ck_suggestion_submitter_matches_source",
        ),
        sa.UniqueConstraint("submitted_by_api_key_id", "idempotency_key", name="uq_suggestion_key_idempotency"),
    )
    op.create_index("ix_suggestion_jurisdiction_id", "suggestion", ["jurisdiction_id"], unique=False)
    op.create_index("ix_suggestion_normalized_url", "suggestion", ["normalized_url"], unique=False)
    op.create_index("ix_suggestion_status_created_at", "suggestion", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_suggestion_status_created_at", table_name="suggestion")
    op.drop_index("ix_suggestion_normalized_url", table_name="suggestion")
    op.drop_index("ix_suggestion_jurisdiction_id", table_name="suggestion")
    op.drop_table("suggestion")
    suggestion_source.drop(op.get_bind(), checkfirst=True)
    suggestion_status.drop(op.get_bind(), checkfirst=True)
    suggestion_kind.drop(op.get_bind(), checkfirst=True)
