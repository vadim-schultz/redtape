"""ORM models for documents and their requirement edges."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base
from app.models.jurisdiction import Jurisdiction
from app.models.taxonomy import Category, DocumentExternalClassification
from app.url_normalization import normalize_url


class Document(Base):
    """Bureaucratic document type in a jurisdiction scope.

    ``normalized_url`` is derived from ``official_url`` by the ``@validates`` hook below, so every ORM write keeps
    it in step. It is a stored copy for duplicate detection, not a source of truth. Staleness: if ``normalize_url``
    changes, existing values go stale (as ``Suggestion.normalized_url`` already can); the remedy is a new backfill
    migration, not an automatic rebuild job. The column is not unique because legacy data may already hold two
    documents with the same normalised URL.
    """

    __tablename__ = "document"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "slug", name="uq_document_jurisdiction_slug"),
        Index("ix_document_jurisdiction_normalized_url", "jurisdiction_id", "normalized_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    title_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    official_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Wider than official_url: re-encoding in normalize_url can lengthen a 500-character URL.
    normalized_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    jurisdiction: Mapped[Jurisdiction] = relationship("Jurisdiction")
    outgoing_requirements: Mapped[list[DocumentRequirement]] = relationship(
        "DocumentRequirement",
        foreign_keys="DocumentRequirement.parent_document_id",
        back_populates="parent_document",
    )
    categories: Mapped[list[Category]] = relationship("Category", secondary="document_category")
    external_classifications: Mapped[list[DocumentExternalClassification]] = relationship(
        "DocumentExternalClassification",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @validates("official_url")
    def _sync_normalized_url(self, _key: str, value: str | None) -> str | None:
        """Keep ``normalized_url`` equal to ``normalize_url(official_url)``; return the value unchanged."""
        self.normalized_url = None if value is None else normalize_url(value)
        return value


class DocumentRequirement(Base):
    """Directed dependency: parent document requires another document in a jurisdiction scope."""

    __tablename__ = "document_requirement"
    __table_args__ = (
        UniqueConstraint(
            "parent_document_id",
            "required_document_id",
            "jurisdiction_id",
            name="uq_requirement_parent_required_jurisdiction",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'canonical'"))
    notes_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    parent_document: Mapped[Document] = relationship(
        "Document",
        foreign_keys=[parent_document_id],
        back_populates="outgoing_requirements",
    )
    required_document: Mapped[Document] = relationship(
        "Document",
        foreign_keys=[required_document_id],
    )
    jurisdiction: Mapped[Jurisdiction] = relationship("Jurisdiction")
