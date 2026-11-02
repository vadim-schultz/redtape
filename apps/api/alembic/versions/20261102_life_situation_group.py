"""Add the life_situation_group taxonomy tier and life_situation.group_id.

Revision ID: 20261102_life_situation_group
Revises: 20261102_link_table_confidence
Create Date: 2026-11-02

Presentation-only (chapter 2, architecture §4): a new parent tier over the 18 existing
`life_situation` codes so default browsing never has to show more than ~8 choices.
`group_id` is left nullable here, same deploy-order convention `name_i18n`/`description_i18n`
already follow — the seed script back-fills every situation's group as a separate step; a
seed-integrity test, not a DB constraint, guarantees every situation ends up with exactly one.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_life_situation_group"
down_revision: str | None = "20261102_link_table_confidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"


def upgrade() -> None:
    op.create_table(
        "life_situation_group",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("code", name="uq_life_situation_group_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_life_situation_group_code_kebab"),
    )
    op.add_column(
        "life_situation",
        sa.Column("group_id", sa.Uuid(as_uuid=True), sa.ForeignKey("life_situation_group.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("life_situation", "group_id")
    op.drop_table("life_situation_group")
