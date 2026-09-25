"""Add domain and life situation taxonomy tables.

Revision ID: 20260625_taxonomy
Revises: 20260610_fix_dup_juris
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260625_taxonomy"
down_revision: Union[str, None] = "20260610_fix_dup_juris"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"


def _term_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("code", name=f"uq_{name}_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name=f"ck_{name}_code_kebab"),
    )


def _link_table(name: str, term: str) -> None:
    op.create_table(
        name,
        sa.Column("document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(f"{term}_id", sa.Uuid(as_uuid=True), sa.ForeignKey(f"{term}.id", ondelete="CASCADE"), primary_key=True),
    )


def upgrade() -> None:
    _term_table("domain")
    _term_table("life_situation")
    _link_table("document_domain", "domain")
    _link_table("document_life_situation", "life_situation")


def downgrade() -> None:
    op.drop_table("document_life_situation")
    op.drop_table("document_domain")
    op.drop_table("life_situation")
    op.drop_table("domain")
