"""Add supported_locale.machine_translated: a locale enabled on machine-made strings says so.

Revision ID: 20261112_locale_machine_flag
Revises: 20261111_snapshot_translation
Create Date: 2026-11-12

The column is NOT NULL and defaults to false, so every existing locale reads as not machine translated until
``enable_locale.py`` enables it on a ``machine_accepted`` status, in the same update that sets ``enabled``. The
downgrade drops the column only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261112_locale_machine_flag"
down_revision: str | None = "20261111_snapshot_translation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "supported_locale",
        sa.Column("machine_translated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("supported_locale", "machine_translated")
