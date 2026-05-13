"""Wave 1: jurisdiction + document + document_requirement.

Revision ID: 20260506_wave1_graph
Revises: 20260505_i18n
Create Date: 2026-05-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260506_wave1_graph"
down_revision: Union[str, None] = "20260505_i18n"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

jurisdiction_kind = postgresql.ENUM(
    "COUNTRY",
    "REGION",
    "MUNICIPALITY",
    name="jurisdiction_kind",
    create_type=True,
)


def upgrade() -> None:
    op.create_table(
        "jurisdiction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", jurisdiction_kind, nullable=False),
        sa.Column("geographic_parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column(
            "administrative_roles",
            postgresql.ARRAY(sa.String(length=64)),
            server_default=sa.text("'{}'::character varying[]"),
            nullable=False,
        ),
        sa.Column(
            "name_i18n",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["geographic_parent_id"],
            ["jurisdiction.id"],
            name="fk_jurisdiction_geographic_parent_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jurisdiction"),
        sa.UniqueConstraint(
            "geographic_parent_id",
            "code",
            name="uq_jurisdiction_parent_code",
        ),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("jurisdiction_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column(
            "title_i18n",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "description_i18n",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("official_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdiction.id"],
            name="fk_document_jurisdiction_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document"),
        sa.UniqueConstraint(
            "jurisdiction_id",
            "slug",
            name="uq_document_jurisdiction_slug",
        ),
    )
    op.create_index(
        "ix_document_jurisdiction_id",
        "document",
        ["jurisdiction_id"],
        unique=False,
    )

    op.create_table(
        "document_requirement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_document_id", sa.Uuid(), nullable=False),
        sa.Column("required_document_id", sa.Uuid(), nullable=False),
        sa.Column("jurisdiction_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), server_default=sa.text("'canonical'"), nullable=False),
        sa.Column("notes_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdiction.id"],
            name="fk_document_requirement_jurisdiction_id_jurisdiction",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_document_id"],
            ["document.id"],
            name="fk_document_requirement_parent_document_id_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["required_document_id"],
            ["document.id"],
            name="fk_document_requirement_required_document_id_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_requirement"),
        sa.UniqueConstraint(
            "parent_document_id",
            "required_document_id",
            "jurisdiction_id",
            name="uq_requirement_parent_required_jurisdiction",
        ),
    )
    op.create_index(
        "ix_document_requirement_jurisdiction_id",
        "document_requirement",
        ["jurisdiction_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_requirement_parent_document_id",
        "document_requirement",
        ["parent_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_requirement_required_document_id",
        "document_requirement",
        ["required_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_requirement_required_document_id", table_name="document_requirement")
    op.drop_index("ix_document_requirement_parent_document_id", table_name="document_requirement")
    op.drop_index("ix_document_requirement_jurisdiction_id", table_name="document_requirement")
    op.drop_table("document_requirement")
    op.drop_index("ix_document_jurisdiction_id", table_name="document")
    op.drop_table("document")
    op.drop_table("jurisdiction")
    jurisdiction_kind.drop(op.get_bind(), checkfirst=True)
