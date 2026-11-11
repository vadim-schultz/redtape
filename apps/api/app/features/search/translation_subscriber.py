"""The search side of the translation-stored event: a translation becomes searchable as soon as it is stored."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.features.search.service import SearchTextService
from app.features.translation.events import StoredSubscriber
from app.features.translation.store import TranslationPayload


def refresh_search_text_on_stored(session: Session) -> StoredSubscriber:
    """Return the subscriber that refreshes the search text of the stored locale in the event's transaction."""
    service = SearchTextService.for_session(session)

    def on_translation_stored(candidate_id: UUID, locale: str, payload: TranslationPayload) -> None:
        service.refresh_locale(candidate_id, locale, payload)

    return on_translation_stored
