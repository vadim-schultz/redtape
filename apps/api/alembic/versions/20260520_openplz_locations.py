"""Wave 2: OpenPLZ location hierarchy.

Revision ID: 20260520_openplz_locations
Revises: 20260506_wave1_graph
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_openplz_locations"
down_revision: Union[str, None] = "20260506_wave1_graph"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Jurisdiction extensions (OpenPLZ-derived).
    op.add_column("jurisdiction", sa.Column("type", sa.String(length=128), nullable=True))
    op.add_column("jurisdiction", sa.Column("postal_code", sa.String(length=16), nullable=True))
    op.add_column(
        "jurisdiction",
        sa.Column(
            "multiple_postal_codes",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "jurisdiction",
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_jurisdiction_code",
        "jurisdiction",
        ["code"],
        unique=False,
    )
    op.create_index(
        "ix_jurisdiction_postal_code",
        "jurisdiction",
        ["postal_code"],
        unique=False,
    )

    # Locality: postal code + locality name under a municipality.
    op.create_table(
        "locality",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("municipality_id", sa.Uuid(), nullable=False),
        sa.Column("postal_code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column(
            "name_i18n",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["municipality_id"],
            ["jurisdiction.id"],
            name="fk_locality_municipality_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_locality"),
        sa.UniqueConstraint(
            "municipality_id",
            "postal_code",
            "name",
            name="uq_locality_municipality_postal_name",
        ),
    )

    op.create_index(
        "ix_locality_municipality_id",
        "locality",
        ["municipality_id"],
        unique=False,
    )
    op.create_index(
        "ix_locality_postal_code",
        "locality",
        ["postal_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_locality_postal_code", table_name="locality")
    op.drop_index("ix_locality_municipality_id", table_name="locality")
    op.drop_table("locality")

    op.drop_index("ix_jurisdiction_postal_code", table_name="jurisdiction")
    op.drop_index("ix_jurisdiction_code", table_name="jurisdiction")

    op.drop_column("jurisdiction", "last_updated")
    op.drop_column("jurisdiction", "multiple_postal_codes")
    op.drop_column("jurisdiction", "postal_code")
    op.drop_column("jurisdiction", "type")

