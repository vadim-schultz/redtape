"""Add partial unique index closing the pending-duplicate race window (D4).

Revision ID: 20260928b_pending_url_unique
Revises: 20260928_suggestion
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260928b_pending_url_unique"
down_revision: Union[str, None] = "20260928_suggestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WHERE = "status = 'pending' AND kind = 'new_document'"


def upgrade() -> None:
    op.create_index(
        "uq_suggestion_pending_url",
        "suggestion",
        ["jurisdiction_id", "normalized_url"],
        unique=True,
        postgresql_where=sa.text(_WHERE),
    )


def downgrade() -> None:
    op.drop_index("uq_suggestion_pending_url", table_name="suggestion")
