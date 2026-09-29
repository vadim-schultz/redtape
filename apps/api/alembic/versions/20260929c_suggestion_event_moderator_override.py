"""Add 'moderator_override' to suggestion_event_type (Chapter 9).

Revision ID: 20260929c_moderator_override
Revises: 20260929b_suggestion_event
Create Date: 2026-09-29
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260929c_moderator_override"
down_revision: Union[str, None] = "20260929b_suggestion_event"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_VALUES = ("submitted", "voted", "status_changed", "promoted")
_NEW_VALUE = "moderator_override"


def upgrade() -> None:
    op.execute(f"ALTER TYPE suggestion_event_type ADD VALUE IF NOT EXISTS '{_NEW_VALUE}'")


def downgrade() -> None:
    # Postgres has no DROP VALUE; recreate the enum without it (D7: no rows should
    # reference it once downgraded, since the feature that wrote them is gone too).
    old_values_sql = ", ".join(f"'{value}'" for value in _OLD_VALUES)
    op.execute("ALTER TABLE suggestion_event ALTER COLUMN event_type TYPE varchar USING event_type::varchar")
    op.execute("DROP TYPE suggestion_event_type")
    op.execute(f"CREATE TYPE suggestion_event_type AS ENUM ({old_values_sql})")
    op.execute(
        "ALTER TABLE suggestion_event ALTER COLUMN event_type "
        "TYPE suggestion_event_type USING event_type::suggestion_event_type"
    )
