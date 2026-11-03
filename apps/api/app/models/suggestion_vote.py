"""ORM model for suggestion votes, one per user."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CK_VALUE = "ck_suggestion_vote_value"
UQ_USER = "uq_suggestion_vote_user"


class SuggestionVote(Base):
    """One user's +1/-1 vote on a suggestion; upserted, never appended."""

    __tablename__ = "suggestion_vote"
    __table_args__ = (
        CheckConstraint("value IN (1, -1)", name=CK_VALUE),
        UniqueConstraint("suggestion_id", "user_id", name=UQ_USER),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("suggestion.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
