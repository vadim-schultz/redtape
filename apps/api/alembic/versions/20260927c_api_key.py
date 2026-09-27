"""Add api_key table.

Revision ID: 20260927c_api_key
Revises: 20260927b_last_seen_at
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260927c_api_key"
down_revision: Union[str, None] = "20260927b_last_seen_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_api_key"),
        sa.UniqueConstraint("key_hash", name="uq_api_key_key_hash"),
    )
    op.create_index("ix_api_key_key_prefix", "api_key", ["key_prefix"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_key_key_prefix", table_name="api_key")
    op.drop_table("api_key")
