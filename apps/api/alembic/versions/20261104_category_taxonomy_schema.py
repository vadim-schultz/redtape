"""Add canonical category, document link, and external classification tables.

Revision ID: 20261104_category_schema
Revises: 20261104_document_normalized_url
Create Date: 2026-11-04

This is the reversible expand step. Legacy taxonomy tables and links remain untouched.
The following backfill revision is forward-only at the data level; downgrading this
revision removes only the additive target projection.
"""

from collections.abc import Callable, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20261104_category_schema"
down_revision: str | None = "20261104_document_normalized_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
CANONICAL_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "category": frozenset(
        {"id", "parent_id", "code", "name_i18n", "description_i18n", "icon", "sort_order", "is_active"}
    ),
    "category_external_mapping": frozenset(
        {
            "id",
            "category_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            "mapping_confidence",
            "mapping_state",
            "reason",
        }
    ),
    "document_category": frozenset({"document_id", "category_id", "confidence", "source", "provenance"}),
    "document_external_classification": frozenset(
        {
            "id",
            "document_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            "source_label",
            "source_path",
            "captured_at",
        }
    ),
}


def upgrade() -> None:
    """Create the additive canonical taxonomy schema."""
    bind = op.get_bind()
    state = _canonical_schema_state(bind)
    if state == "absent":
        _create_canonical_schema()
        return
    if state == "adoptable":
        return
    raise RuntimeError(
        "canonical taxonomy schema drift: expected no pre-existing canonical tables "
        f"or an exact empty schema, got {state}"
    )


def _canonical_schema_state(bind: Connection) -> str:
    """Classify pre-existing canonical tables before the expand migration runs."""
    inspector = sa.inspect(bind)
    expected_tables = set(CANONICAL_TABLE_COLUMNS)
    existing_tables = {table for table in expected_tables if inspector.has_table(table)}
    checks: tuple[tuple[str, Callable[[], bool]], ...] = (
        ("absent", lambda: not existing_tables),
        ("partial", lambda: existing_tables != expected_tables),
        ("column drift", lambda: _has_column_drift(inspector)),
        ("non-empty", lambda: _has_rows(bind)),
    )
    return next((state for state, check in checks if check()), "adoptable")


def _has_column_drift(inspector: sa.Inspector) -> bool:
    """Return whether an existing canonical table has an unexpected column set."""
    return any(
        {column["name"] for column in inspector.get_columns(table)} != expected_columns
        for table, expected_columns in CANONICAL_TABLE_COLUMNS.items()
    )


def _has_rows(bind: Connection) -> bool:
    """Return whether an existing canonical table contains data that this migration did not create."""
    return any(
        bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None
        for table in CANONICAL_TABLE_COLUMNS
    )


def _create_canonical_schema() -> None:
    """Create the additive canonical taxonomy schema on a fresh database."""
    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("parent_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description_i18n", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["parent_id"], ["category.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", name="uq_category_code"),
        sa.CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_category_code_kebab"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_category_not_its_own_parent"),
    )
    op.create_index("ix_category_parent_id", "category", ["parent_id"], unique=False)
    op.create_table(
        "category_external_mapping",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("external_level", sa.String(length=32), nullable=False),
        sa.Column("external_code", sa.String(length=128), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("mapping_confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("mapping_state", sa.String(length=32), nullable=False, server_default=sa.text("'mapped'")),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "category_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            name="uq_category_external_mapping_key",
        ),
        sa.CheckConstraint(
            "mapping_confidence >= 0 AND mapping_confidence <= 1",
            name="ck_category_mapping_confidence",
        ),
    )
    op.create_index("ix_category_external_mapping_category_id", "category_external_mapping", ["category_id"])
    op.create_table(
        "document_category",
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("source", sa.String(length=64), nullable=False, server_default=sa.text("'legacy_crosswalk'")),
        sa.Column("provenance", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "category_id"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_category_confidence"),
    )
    op.create_table(
        "document_external_classification",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("external_level", sa.String(length=32), nullable=False),
        sa.Column("external_code", sa.String(length=128), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("source_label", sa.String(length=500), nullable=True),
        sa.Column("source_path", postgresql.JSONB(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "document_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            name="uq_document_external_classification_key",
        ),
    )
    op.create_index(
        "ix_document_external_classification_document_id",
        "document_external_classification",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove only the additive target projection; legacy links remain available."""
    op.drop_index("ix_document_external_classification_document_id", table_name="document_external_classification")
    op.drop_table("document_external_classification")
    op.drop_table("document_category")
    op.drop_index("ix_category_external_mapping_category_id", table_name="category_external_mapping")
    op.drop_table("category_external_mapping")
    op.drop_index("ix_category_parent_id", table_name="category")
    op.drop_table("category")
