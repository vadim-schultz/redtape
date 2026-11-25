"""ORM models for stored translations: the index row per candidate and locale, and the translation task queue.

The translated text is not here. It lives in object storage (decision D17); the index row answers the cheap
questions: does a translation exist, is it stale, who made it and which object holds the text.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import enum_values
from app.models.discovery.mixins import TimestampMixin
from app.models.search import WorkTaskStatus

TRANSLATION_SOURCE_ENUM: Final = "translation_source"
"""Name of the native PostgreSQL enum; the migration creates the same type."""


def _candidate_fk() -> ForeignKey:
    """Return a new foreign key to the candidate; rows disappear with their candidate."""
    return ForeignKey("discovery_document_candidate.id", ondelete="CASCADE")


class TranslationSource(enum.StrEnum):
    """Who made a translation: a machine engine, or a person (which a machine write never overwrites)."""

    MT = "mt"
    HUMAN = "human"


class CandidateTranslation(TimestampMixin, Base):
    """The index row of one stored translation, keyed ``(candidate, locale)``; the text is the object at ``storage_key``."""

    __tablename__ = "candidate_translation"

    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _candidate_fk(), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[TranslationSource] = mapped_column(
        SAEnum(TranslationSource, name=TRANSLATION_SOURCE_ENUM, native_enum=True, values_callable=enum_values),
        nullable=False,
        default=TranslationSource.MT,
        server_default=text("'mt'"),
    )
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class TranslationTask(TimestampMixin, Base):
    """A leased unit of work: translate one ``(candidate, locale)`` unit whose German source hash is ``source_hash``."""

    __tablename__ = "translation_task"
    __table_args__ = (
        Index(
            "uq_translation_task_open",
            "candidate_id",
            "locale",
            unique=True,
            postgresql_where=text("status in ('pending', 'claimed')"),
        ),
        Index("ix_translation_task_status_priority_created_at", "status", "priority", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _candidate_fk(), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
