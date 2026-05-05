from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SupportedLocale(Base):
    """Enabled locales for pickers and validation."""

    __tablename__ = "supported_locale"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name_native: Mapped[str] = mapped_column(Text, nullable=False)
    name_english: Mapped[str] = mapped_column(Text, nullable=False)
    flag_emoji: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    completeness_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


class UITranslation(Base):
    """UI strings keyed by dot-notation; DB is the runtime source of truth."""

    __tablename__ = "ui_translation"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
