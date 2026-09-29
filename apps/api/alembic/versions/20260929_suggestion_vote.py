"""Add suggestion_vote table: one +1/-1 vote per (suggestion, user).

Revision ID: 20260929_suggestion_vote
Revises: 20260928e_drop_parent_code_uq
Create Date: 2026-09-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_suggestion_vote"
down_revision: Union[str, None] = "20260928e_drop_parent_code_uq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suggestion_vote",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "suggestion_id", sa.Uuid(as_uuid=True), sa.ForeignKey("suggestion.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("value IN (1, -1)", name="ck_suggestion_vote_value"),
        sa.UniqueConstraint("suggestion_id", "user_id", name="uq_suggestion_vote_user"),
    )


def downgrade() -> None:
    op.drop_table("suggestion_vote")
