"""Per-locale search text from stored translations, and the subscription that keeps it current (chapter 16)."""

from __future__ import annotations

import pytest
from app.features.search.errors import UnsupportedSearchLocaleError
from app.features.search.results import RefreshStatus
from app.features.translation.router import provide_translation_completion
from app.models.search import WorkTaskStatus
from app.schema.translation.machine import TranslationOutcome
from app.shared.object_store import InMemoryObjectStore
from sqlalchemy.orm import Session

from search_locale_support import (
    TURKISH_DESCRIPTION,
    TURKISH_TITLE,
    embedding_tasks,
    keyword_hits,
    payload,
    search_text_row,
)
from search_support import make_candidate, search_service
from translation_support import claimed_by, complete_item, make_key, queued_task


def test_refresh_locale_builds_turkish_text_and_the_turkish_tsvector_matches_an_inflected_query_form(
    db_session: Session,
) -> None:
    candidate = make_candidate(db_session, "Kindergeldantrag")

    result = search_service(db_session).refresh_locale(candidate.id, "tr", payload())

    row = search_text_row(db_session, candidate, "tr")
    assert row is not None
    assert (result.status, row.text) == (RefreshStatus.WRITTEN, f"{TURKISH_TITLE} {TURKISH_DESCRIPTION}")
    assert keyword_hits(db_session, "kimlik", "tr") == [candidate.id]
    assert keyword_hits(db_session, "kimlik", "en") == []


def test_refresh_locale_leaves_an_unchanged_text_untouched(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    service = search_service(db_session)
    service.refresh_locale(candidate.id, "tr", payload())

    again = service.refresh_locale(candidate.id, "tr", payload())

    assert again.status is RefreshStatus.UNCHANGED
    assert len(embedding_tasks(db_session, "tr")) == 1


@pytest.mark.parametrize("title", ["", "   "])
def test_refresh_locale_with_a_missing_or_empty_title_produces_no_row(db_session: Session, title: str) -> None:
    candidate = make_candidate(db_session)

    result = search_service(db_session).refresh_locale(candidate.id, "tr", payload(title=title))

    assert result.status is RefreshStatus.SKIPPED_EMPTY
    assert search_text_row(db_session, candidate, "tr") is None
    assert embedding_tasks(db_session) == []


@pytest.mark.parametrize("locale", ["xx", "de"])
def test_refresh_locale_with_an_unsupported_or_canonical_locale_is_an_error(db_session: Session, locale: str) -> None:
    candidate = make_candidate(db_session)

    with pytest.raises(UnsupportedSearchLocaleError):
        search_service(db_session).refresh_locale(candidate.id, locale, payload(locale=locale))

    assert search_text_row(db_session, candidate, locale) is None


def test_a_stored_translation_is_keyword_searchable_without_the_embed_drain(db_session: Session) -> None:
    candidate, task = queued_task(db_session, "tr")
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    item = complete_item(task, db_session, title=TURKISH_TITLE, description=TURKISH_DESCRIPTION)

    (result,) = provide_translation_completion(db_session, InMemoryObjectStore()).complete(key.id, [item])

    assert result.outcome is TranslationOutcome.STORED
    assert keyword_hits(db_session, "kimlik", "tr") == [candidate.id]
    (embedding,) = embedding_tasks(db_session, "tr")
    assert embedding.status is WorkTaskStatus.PENDING


def test_a_stale_translation_writes_no_search_text(db_session: Session) -> None:
    candidate, task = queued_task(db_session, "tr")
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    item = complete_item(task, db_session, source_hash="not-the-current-hash", title=TURKISH_TITLE)

    (result,) = provide_translation_completion(db_session, InMemoryObjectStore()).complete(key.id, [item])

    assert result.outcome is TranslationOutcome.STALE
    assert search_text_row(db_session, candidate, "tr") is None
    assert embedding_tasks(db_session, "tr") == []
