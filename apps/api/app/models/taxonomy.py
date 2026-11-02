from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, String, Table, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

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
