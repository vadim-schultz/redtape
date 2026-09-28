from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CK_SUBMITTER_MATCHES_SOURCE = "ck_suggestion_submitter_matches_source"
UQ_KEY_IDEMPOTENCY = "uq_suggestion_key_idempotency"
UQ_PENDING_URL = "uq_suggestion_pending_url"
_PENDING_NEW_DOCUMENT_WHERE = "status = 'pending' AND kind = 'new_document'"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class SuggestionKind(enum.StrEnum):
    """What a suggestion proposes to add to the catalogue."""

    NEW_DOCUMENT = "new_document"
    NEW_REQUIREMENT = "new_requirement"


class SuggestionStatus(enum.StrEnum):
    """Moderation state; this suite only ever creates `pending`."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SuggestionSource(enum.StrEnum):
    """Who submitted a suggestion, derived from the authenticated principal."""

    HUMAN = "human"
    CRAWLER = "crawler"


class Suggestion(Base):
    """A proposed catalogue change (new document or requirement edge) awaiting moderation."""

    __tablename__ = "suggestion"
    __table_args__ = (
        CheckConstraint(
            "(source_type = 'human' AND submitted_by_api_key_id IS NULL) "
            "OR (source_type = 'crawler' AND submitted_by_user_id IS NULL)",
            name=CK_SUBMITTER_MATCHES_SOURCE,
        ),
        UniqueConstraint("submitted_by_api_key_id", "idempotency_key", name=UQ_KEY_IDEMPOTENCY),
        Index("ix_suggestion_status_created_at", "status", "created_at"),
        Index(
            UQ_PENDING_URL,
            "jurisdiction_id",
            "normalized_url",
            unique=True,
            postgresql_where=text(_PENDING_NEW_DOCUMENT_WHERE),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[SuggestionKind] = mapped_column(
        SAEnum(SuggestionKind, name="suggestion_kind", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        SAEnum(SuggestionStatus, name="suggestion_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=SuggestionStatus.PENDING,
        server_default=text("'pending'"),
    )
    source_type: Mapped[SuggestionSource] = mapped_column(
        SAEnum(SuggestionSource, name="suggestion_source", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    submitted_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jurisdiction.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
