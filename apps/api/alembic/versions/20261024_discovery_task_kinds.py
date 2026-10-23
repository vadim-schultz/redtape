"""Add crawl task kinds and discovery_task.input_key.

Revision ID: 20261024_task_kinds
Revises: 20261023_discovery_run
Create Date: 2026-10-24

Postgres cannot remove enum labels, so the downgrade drops ``input_key`` only
and leaves ``harvest_payload``, ``extract_page`` and ``capture_screenshot`` in
``discovery_task_kind``. The labels are inert: the claim route serves only the
legacy kinds unless a worker asks for more.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261024_task_kinds"
down_revision: str | None = "20261023_discovery_run"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TASK_KINDS: tuple[str, ...] = ("harvest_payload", "extract_page", "capture_screenshot")


def _add_enum_labels() -> None:
    """Add the new labels outside a transaction, as ``ADD VALUE`` requires."""
    with op.get_context().autocommit_block():
        for label in NEW_TASK_KINDS:
            op.execute(f"ALTER TYPE discovery_task_kind ADD VALUE IF NOT EXISTS '{label}'")


def upgrade() -> None:
    _add_enum_labels()
    op.add_column("discovery_task", sa.Column("input_key", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("discovery_task", "input_key")
