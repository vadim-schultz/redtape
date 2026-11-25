"""ORM models for snapshot translations: the index row per procedure page and locale, and the snapshot task queue.

A snapshot is the cleaned text of one procedure page, stored as blocks in object storage (decision D6). The index row
records the object key and hashes, or the reason the page was skipped. The unit is the page (decision D1), so every
candidate on one page shares one row per locale.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import enum_values
from app.models.discovery.mixins import TimestampMixin
from app.models.search import WorkTaskStatus

CK_STORAGE_XOR_SKIP = "ck_snapshot_translation_storage_xor_skip"
"""A stored page has an object key and no skip reason; a skipped page has a reason and no key."""


def _catalogue_fk() -> ForeignKey:
    """Return a new foreign key to the catalogue row; rows disappear with their catalogue row."""
    return ForeignKey("catalogue_service.id", ondelete="CASCADE")


class SnapshotTranslation(TimestampMixin, Base):
    """The index row of one page's translation in one locale, keyed ``(catalogue row, locale)``."""

    __tablename__ = "snapshot_translation"
    __table_args__ = (CheckConstraint("storage_key IS NULL OR skipped_reason IS NULL", name=CK_STORAGE_XOR_SKIP),)

    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _catalogue_fk(), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    skipped_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)


class SnapshotTranslationTask(TimestampMixin, Base):
    """A leased unit of work: translate one page into one locale, queued against ``source_hash``.

    ``artifact_id`` and ``artifact_sha256`` name the artifact the worker read, so a claim fills them, not the enqueue.
    """

    __tablename__ = "snapshot_translation_task"
    __table_args__ = (
        Index(
            "uq_snapshot_translation_task_open",
            "catalogue_service_id",
            "locale",
            unique=True,
            postgresql_where=text("status in ('pending', 'claimed')"),
        ),
        Index("ix_snapshot_translation_task_status_priority_created_at", "status", "priority", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), _catalogue_fk(), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_artifact.id", ondelete="SET NULL"), nullable=True
    )
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
