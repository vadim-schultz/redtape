"""Persistence for supported locales and their UI translation strings."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.locale import SupportedLocale, UITranslation


class LocalesRepository:
    """DB reads backing the locales and translations endpoints."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to a request-scoped session."""
        self._session = session

    def list_enabled(self) -> Sequence[SupportedLocale]:
        """Every enabled locale, ordered by code."""
        stmt = select(SupportedLocale).where(SupportedLocale.enabled.is_(True)).order_by(SupportedLocale.code)
        return self._session.scalars(stmt).all()

    def translations_for(self, code: str) -> Sequence[tuple[str, str]]:
        """Every `(key, value)` UI translation row stored for `code`; empty when there are none."""
        stmt = select(UITranslation.key, UITranslation.value).where(UITranslation.locale == code)
        return [(key, value) for key, value in self._session.execute(stmt).all()]
