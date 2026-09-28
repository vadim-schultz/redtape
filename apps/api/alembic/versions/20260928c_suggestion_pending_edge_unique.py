"""Add partial unique index closing the pending-edge-duplicate race window (chapter 8).

Revision ID: 20260928c_pending_edge_unique
Revises: 20260928b_pending_url_unique
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260928c_pending_edge_unique"
down_revision: Union[str, None] = "20260928b_pending_url_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WHERE = "status = 'pending' AND kind = 'new_requirement'"


def upgrade() -> None:
    op.create_index(
        "uq_suggestion_pending_edge",
        "suggestion",
        [
            "jurisdiction_id",
            sa.text("(payload->>'parent_document_id')"),
            sa.text("(payload->>'required_document_id')"),
        ],
        unique=True,
        postgresql_where=sa.text(_WHERE),
    )


def downgrade() -> None:
    op.drop_index("uq_suggestion_pending_edge", table_name="suggestion")
