"""Add suggestion_event table: an immutable log of what happened to a suggestion.

Revision ID: 20260929b_suggestion_event
Revises: 20260929_suggestion_vote
Create Date: 2026-09-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929b_suggestion_event"
down_revision: Union[str, None] = "20260929_suggestion_vote"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

suggestion_event_type = postgresql.ENUM(
    "submitted", "voted", "status_changed", "promoted", name="suggestion_event_type", create_type=True
)


def upgrade() -> None:
    op.create_table(
        "suggestion_event",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "suggestion_id", sa.Uuid(as_uuid=True), sa.ForeignKey("suggestion.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("event_type", suggestion_event_type, nullable=False),
        sa.Column("data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "actor_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "actor_api_key_id", sa.Uuid(as_uuid=True), sa.ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "NOT (actor_user_id IS NOT NULL AND actor_api_key_id IS NOT NULL)",
            name="ck_suggestion_event_actor_exclusive",
        ),
    )
    op.create_index("ix_suggestion_event_suggestion_id", "suggestion_event", ["suggestion_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_suggestion_event_suggestion_id", table_name="suggestion_event")
    op.drop_table("suggestion_event")
    suggestion_event_type.drop(op.get_bind(), checkfirst=True)
