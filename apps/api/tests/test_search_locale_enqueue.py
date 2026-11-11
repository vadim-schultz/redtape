"""Locale-aware, gated embedding enqueue of translated text (chapter 16)."""

from __future__ import annotations

import pytest
from app.config import settings
from app.features.search.enqueue import EmbeddingEnqueuer, EnqueueOutcome
from app.features.search.hashing import content_hash
from app.features.search.text import BuiltText
from sqlalchemy.orm import Session

from search_locale_support import embedding_tasks, payload, search_text_row
from search_support import embed, make_candidate, search_service


def _built(text: str, locale: str = "tr") -> BuiltText:
    return BuiltText(locale=locale, text=text, content_hash=content_hash(text))


def test_a_changed_locale_hash_enqueues_one_embedding_task_for_candidate_model_and_locale(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    service = search_service(db_session)

    first = service.refresh_locale(candidate.id, "tr", payload(title="Birinci"))
    second = service.refresh_locale(candidate.id, "tr", payload(title="İkinci"))

    (task,) = embedding_tasks(db_session)
    assert (first.enqueued, second.enqueued) == (True, True)
    assert (task.candidate_id, task.model, task.locale) == (candidate.id, settings.embedding_model, "tr")
    assert task.text_hash == search_text_row(db_session, candidate, "tr").content_hash  # type: ignore[union-attr]


def test_an_unchanged_locale_hash_enqueues_nothing(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    built = _built("aynı metin")
    embed(db_session, candidate, built.content_hash, built.locale)

    outcome = EmbeddingEnqueuer(db_session, settings.embedding_model).enqueue(candidate.id, built)

    assert outcome is EnqueueOutcome.CURRENT
    assert embedding_tasks(db_session) == []


def test_a_german_embedding_does_not_stand_in_for_a_translated_locale(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    embed(db_session, candidate, _built("Kindergeld", "de").content_hash)

    outcome = EmbeddingEnqueuer(db_session, settings.embedding_model).enqueue(candidate.id, _built("Kindergeld", "tr"))

    assert outcome is EnqueueOutcome.QUEUED
    assert [task.locale for task in embedding_tasks(db_session)] == ["tr"]


def test_a_locale_outside_the_embedding_locales_gets_search_text_but_no_embedding_task(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "embedding_locales", "de en")
    candidate = make_candidate(db_session)

    result = search_service(db_session).refresh_locale(candidate.id, "tr", payload())

    assert search_text_row(db_session, candidate, "tr") is not None
    assert (result.status.value, result.enqueued) == ("written", False)
    assert embedding_tasks(db_session) == []


def test_the_enqueuer_reports_a_gated_locale_and_leaves_the_queue_alone(db_session: Session) -> None:
    candidate = make_candidate(db_session)

    gated = EmbeddingEnqueuer(db_session, settings.embedding_model, locales=("de",)).enqueue(candidate.id, _built("x"))
    allowed = EmbeddingEnqueuer(db_session, settings.embedding_model, locales=("de", "tr")).enqueue(
        candidate.id, _built("x")
    )

    assert (gated, allowed) == (EnqueueOutcome.NOT_EMBEDDED, EnqueueOutcome.QUEUED)
    assert len(embedding_tasks(db_session)) == 1
