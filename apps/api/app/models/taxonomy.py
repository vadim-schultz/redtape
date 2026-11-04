"""ORM models for legacy axes and the canonical category taxonomy."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document

CODE_PATTERN = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"


class TaxonomyTermMixin:
    """Columns shared by both matrix axes; `code` is a stable, untranslated identifier."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class Domain(TaxonomyTermMixin, Base):
    """Subject area a document belongs to (matrix rows)."""

    __tablename__ = "domain"
    __table_args__ = (
        UniqueConstraint("code", name="uq_domain_code"),
        CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_domain_code_kebab"),
    )


class LifeSituationGroup(TaxonomyTermMixin, Base):
    """Presentational parent tier over the life-situation axis (~8 groups, architecture §4)."""

    __tablename__ = "life_situation_group"
    __table_args__ = (
        UniqueConstraint("code", name="uq_life_situation_group_code"),
        CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_life_situation_group_code_kebab"),
    )


class LifeSituation(TaxonomyTermMixin, Base):
    """Life event that triggers a set of documents (matrix columns)."""

    __tablename__ = "life_situation"
    __table_args__ = (
        UniqueConstraint("code", name="uq_life_situation_code"),
        CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_life_situation_code_kebab"),
    )

    # Nullable at the schema level only so a migration can land before the seed script
    # back-fills every row's group; a seed-integrity test, not this column, guarantees
    # every situation ends up with exactly one group (chapter 2 design).
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("life_situation_group.id"), nullable=True)


class Category(Base):
    """Canonical self-referential category tree row."""

    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("code", name="uq_category_code"),
        CheckConstraint(f"code ~ '{CODE_PATTERN}'", name="ck_category_code_kebab"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_category_not_its_own_parent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_i18n: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    external_mappings: Mapped[list[CategoryExternalMapping]] = relationship(
        "CategoryExternalMapping",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class CategoryExternalMapping(Base):
    """Mapping from a canonical category to a versioned external taxonomy code."""

    __tablename__ = "category_external_mapping"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            name="uq_category_external_mapping_key",
        ),
        CheckConstraint("mapping_confidence >= 0 AND mapping_confidence <= 1", name="ck_category_mapping_confidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_level: Mapped[str] = mapped_column(String(32), nullable=False)
    external_code: Mapped[str] = mapped_column(String(128), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("1.0"))
    mapping_state: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'mapped'"))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    category: Mapped[Category] = relationship("Category", back_populates="external_mappings")


class DocumentExternalClassification(Base):
    """External source fact attached to a document without changing its category code."""

    __tablename__ = "document_external_classification"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "source",
            "external_level",
            "external_code",
            "source_version",
            name="uq_document_external_classification_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_level: Mapped[str] = mapped_column(String(32), nullable=False)
    external_code: Mapped[str] = mapped_column(String(128), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_path: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="external_classifications")


category_external_mapping = CategoryExternalMapping.__table__
document_external_classification = DocumentExternalClassification.__table__


def _link_table(name: str, term: str, *extra_columns: Column) -> Table:
    return Table(
        name,
        Base.metadata,
        Column("document_id", Uuid(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
        Column(f"{term}_id", Uuid(as_uuid=True), ForeignKey(f"{term}.id", ondelete="CASCADE"), primary_key=True),
        Column("confidence", Float, nullable=False, server_default=text("1.0")),
        *extra_columns,
    )


document_domain = _link_table("document_domain", "domain")
document_life_situation = _link_table(
    "document_life_situation",
    "life_situation",
    # The leaf-refinement facet is situation-only (chapter 3's own "Out of scope") — never added to
    # document_domain, where a domain hint only ever contributes to scoring, not a browsable facet.
    Column("pvog_leaf_code", String(64), nullable=True),
)

document_category = Table(
    "document_category",
    Base.metadata,
    Column("document_id", Uuid(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Uuid(as_uuid=True), ForeignKey("category.id", ondelete="CASCADE"), primary_key=True),
    Column("confidence", Float, nullable=False, server_default=text("1.0")),
    Column("source", String(64), nullable=False, server_default=text("'legacy_crosswalk'")),
    Column("provenance", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_category_confidence"),
)
