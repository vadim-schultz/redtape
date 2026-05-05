"""Wave 0: supported_locale + ui_translation.

Revision ID: 20260505_i18n
Revises:
Create Date: 2026-05-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_i18n"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supported_locale",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name_native", sa.Text(), nullable=False),
        sa.Column("name_english", sa.Text(), nullable=False),
        sa.Column("flag_emoji", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "completeness_pct",
            sa.Float(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "ui_translation",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", "locale"),
    )
    op.create_index(
        "idx_ui_translation_locale",
        "ui_translation",
        ["locale"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_ui_translation_locale", table_name="ui_translation")
    op.drop_table("ui_translation")
    op.drop_table("supported_locale")
