from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Uuid, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CK_ACTOR_EXCLUSIVE = "ck_suggestion_event_actor_exclusive"


def _enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class EventType(enum.StrEnum):
    """What kind of thing happened to a suggestion."""

    SUBMITTED = "submitted"
    VOTED = "voted"
    STATUS_CHANGED = "status_changed"
    PROMOTED = "promoted"


class SuggestionEvent(Base):
    """An immutable record of one thing that happened to a suggestion (Chapter 8)."""

    __tablename__ = "suggestion_event"
    __table_args__ = (
        CheckConstraint("NOT (actor_user_id IS NOT NULL AND actor_api_key_id IS NOT NULL)", name=CK_ACTOR_EXCLUSIVE),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("suggestion.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="suggestion_event_type", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    actor_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
