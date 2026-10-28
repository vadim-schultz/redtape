"""Add the llm_extract kind, the issued role, mention conditions and tags, and discovery_candidate_edge.

Revision ID: 20261029_staging_edges
Revises: 20261028_budget_ledger
Create Date: 2026-10-29

Everything is additive. ``llm_extract`` (``discovery_task_kind``) and ``issued``
(``discovery_mention_role``) are new enum labels; ``discovery_candidate_mention`` gains nullable
``condition``, ``is_optional``, ``domain_codes`` and ``situation_codes``; ``discovery_candidate_edge``
stages ``parent requires required`` edges with the procedure as provenance. Postgres cannot remove
enum labels, so the downgrade leaves both labels in place (they are inert) and drops the rest.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261029_staging_edges"
down_revision: str | None = "20261028_budget_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASIS_ENUM = postgresql.ENUM("explicit", "derived_single_issued", name="discovery_edge_basis", create_type=False)
NEW_ENUM_LABELS: tuple[tuple[str, str], ...] = (
    ("discovery_task_kind", "llm_extract"),
    ("discovery_mention_role", "issued"),
)
EDGE_TABLE = "discovery_candidate_edge"
MENTION_TABLE = "discovery_candidate_mention"


def _add_enum_labels() -> None:
    """Add the new labels outside a transaction, as ``ADD VALUE`` requires."""
    with op.get_context().autocommit_block():
        for type_name, label in NEW_ENUM_LABELS:
            op.execute(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{label}'")


def _add_mention_columns() -> None:
    op.add_column(MENTION_TABLE, sa.Column("condition", sa.Text(), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("is_optional", sa.Boolean(), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("domain_codes", sa.ARRAY(sa.String(length=64)), nullable=True))
    op.add_column(MENTION_TABLE, sa.Column("situation_codes", sa.ARRAY(sa.String(length=64)), nullable=True))


def _create_edge_table() -> None:
    op.create_table(
        EDGE_TABLE,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("required_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_service_id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("is_optional", sa.Boolean(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("basis", BASIS_ENUM, nullable=False),
        sa.Column("extractor", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("parent_candidate_id <> required_candidate_id", name="ck_discovery_candidate_edge_distinct"),
        sa.ForeignKeyConstraint(["parent_candidate_id"], ["discovery_document_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["required_candidate_id"], ["discovery_document_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catalogue_service_id"], ["catalogue_service.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_candidate_id", "required_candidate_id", "catalogue_service_id", name="uq_discovery_candidate_edge_key"
        ),
    )
    for column in ("parent_candidate_id", "required_candidate_id", "catalogue_service_id"):
        op.create_index(f"ix_{EDGE_TABLE}_{column}", EDGE_TABLE, [column])


def upgrade() -> None:
    _add_enum_labels()
    BASIS_ENUM.create(op.get_bind(), checkfirst=True)
    _add_mention_columns()
    _create_edge_table()


def downgrade() -> None:
    op.drop_table(EDGE_TABLE)
    BASIS_ENUM.drop(op.get_bind(), checkfirst=True)
    for column in ("situation_codes", "domain_codes", "is_optional", "condition"):
        op.drop_column(MENTION_TABLE, column)
