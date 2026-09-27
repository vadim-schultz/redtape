"""Add app_user table and user_role enum.

Revision ID: 20260927_app_user
Revises: 20260625_taxonomy
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260927_app_user"
down_revision: Union[str, None] = "20260625_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "user",
    "moderator",
    "admin",
    name="user_role",
    create_type=True,
)


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("role", user_role, server_default=sa.text("'user'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_app_user"),
    )
    op.create_index("uq_app_user_email_lower", "app_user", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_app_user_email_lower", table_name="app_user")
    op.drop_table("app_user")
    user_role.drop(op.get_bind(), checkfirst=True)
