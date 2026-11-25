"""ORM models for search: per-candidate search text, embeddings and the embedding task queue.

Nothing here is a source of truth. The rows are derived from candidates (and later from stored translations), so they
can be rebuilt; they are keyed so per-locale text and entity resolution can be added without a schema change.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Final

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import enum_values
from app.models.discovery.mixins import CreatedAtMixin, TimestampMixin

EMBEDDING_DIM: Final = 1024
"""Native output width of the embedding model (chapter 1 probe). The migration freezes the same literal."""

CANONICAL_LOCALE: Final = "de"
"""Locale of the canonical text a candidate is searched and embedded in; other locales are extra rows."""


def _candidate_fk() -> ForeignKey:
    """Return a new foreign key to the candidate; rows disappear with their candidate."""
    return ForeignKey("discovery_document_candidate.id", ondelete="CASCADE")


class WorkTaskStatus(enum.StrEnum):
    """Lifecycle of a leased worker task; shared by every dedicated work queue."""

    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"


class CandidateSearchText(Base):
    """The text of one candidate in one locale, with the full-text vectors that search reads.

    The vectors are plain columns written by the builder: ``unaccent()`` is not immutable, so they cannot be generated.
    ``tsv_native`` uses the text-search configuration of the locale, ``tsv_simple`` the ``simple`` one.
    """

    __tablename__ = "candidate_search_text"
    __table_args__ = (
        Index("ix_candidate_search_text_tsv_native", "tsv_native", postgresql_using="gin"),
        Index("ix_candidate_search_text_tsv_simple", "tsv_simple", postgresql_using="gin"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _candidate_fk(), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tsv_native: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    tsv_simple: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CandidateEmbedding(CreatedAtMixin, Base):
    """One embedding per candidate, model and locale; ``locale`` names the search text it was computed from."""

    __tablename__ = "candidate_embedding"
    __table_args__ = (
        Index(
            "ix_candidate_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _candidate_fk(), primary_key=True)
    model: Mapped[str] = mapped_column(String(100), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(HALFVEC(EMBEDDING_DIM), nullable=False)


class EmbeddingTask(TimestampMixin, Base):
    """A leased unit of work: embed one ``(candidate, model, locale)`` text whose hash is ``text_hash``."""

    __tablename__ = "embedding_task"
    __table_args__ = (
        Index(
            "uq_embedding_task_open",
            "candidate_id",
            "model",
            "locale",
            unique=True,
            postgresql_where=text("status in ('pending', 'claimed')"),
        ),
        Index("ix_embedding_task_status_priority_created_at", "status", "priority", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _candidate_fk(), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[WorkTaskStatus] = mapped_column(
        SAEnum(WorkTaskStatus, name="work_task_status", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=WorkTaskStatus.PENDING,
        server_default=text("'pending'"),
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))
    phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
