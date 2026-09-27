"""Add app_user.last_seen_at.

Revision ID: 20260927b_last_seen_at
Revises: 20260927_app_user
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260927b_last_seen_at"
down_revision: Union[str, None] = "20260927_app_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("app_user", "last_seen_at")
