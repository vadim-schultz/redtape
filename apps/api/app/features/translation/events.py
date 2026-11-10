"""The translation-stored event: a small subscriber list that later chapters extend, with no-op defaults."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.translation.store import TranslationPayload

logger = logging.getLogger(__name__)

StoredSubscriber = Callable[[UUID, str, TranslationPayload], None]
"""``on_translation_stored(candidate_id, locale, payload)``: the payload is the in-memory result, never re-read from storage."""


class TranslationStoredEvents:
    """Tell every subscriber that a translation was stored, each in its own savepoint.

    A subscriber failure is logged and rolled back to its savepoint: the translation stays stored, because the
    derived data a subscriber maintains can always be rebuilt from it.
    """

    def __init__(self, session: Session, subscribers: Sequence[StoredSubscriber] = ()) -> None:
        """Bind the event to ``session`` and its ``subscribers`` (none by default)."""
        self._session = session
        self._subscribers = tuple(subscribers)

    def publish(self, candidate_id: UUID, locale: str, payload: TranslationPayload) -> None:
        """Call every subscriber once with the stored translation."""
        for subscriber in self._subscribers:
            self._call(subscriber, candidate_id, locale, payload)

    def _call(self, subscriber: StoredSubscriber, candidate_id: UUID, locale: str, payload: TranslationPayload) -> None:
        try:
            with self._session.begin_nested():
                subscriber(candidate_id, locale, payload)
        except Exception:
            logger.exception("translation-stored subscriber failed for %s %s", candidate_id, locale)
