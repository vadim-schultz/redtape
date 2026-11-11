"""Pruning one locale's vectors and open tasks (chapter 16)."""

from __future__ import annotations

import pytest
from app.config import settings
from app.models.search import CandidateEmbedding, EmbeddingTask, WorkTaskStatus
from scripts.prune_embeddings import PruneReport, _parse_options, format_report, run_prune
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from search_locale_support import embedding_tasks, payload
from search_query_world import add_embedding, at_similarity
from search_support import make_candidate, search_service


def _vectors(session: Session, locale: str) -> int:
    stmt = select(func.count()).select_from(CandidateEmbedding).where(CandidateEmbedding.locale == locale)
    return int(session.scalar(stmt) or 0)


def _world(session: Session) -> None:
    """Two candidates, each with a de and a tr vector; one tr task pending, one de task pending."""
    for title in ("Kindergeld", "Wohngeld"):
        candidate = make_candidate(session, title)
        for locale in ("de", "tr"):
            add_embedding(session, candidate, at_similarity(0.5), locale=locale)
    pending = make_candidate(session, "Elterngeld")
    search_service(session).refresh_locale(pending.id, "tr", payload())
    session.add(EmbeddingTask(candidate_id=pending.id, model=settings.embedding_model, locale="de", text_hash="h"))
    session.flush()


def test_prune_removes_one_locales_vectors_and_tasks_and_reports_the_space_reclaimed(db_session: Session) -> None:
    _world(db_session)

    report = run_prune(db_session, "tr")

    assert (report.vectors, report.tasks) == (2, 1)
    assert report.bytes_reclaimed >= 2 * 2 * 1024
    assert _vectors(db_session, "tr") == 0
    assert [task.locale for task in embedding_tasks(db_session)] == ["de"]
    assert "tr" in format_report(report) and "2 vectors" in format_report(report)


def test_prune_leaves_other_locales_and_german_rows_untouched(db_session: Session) -> None:
    _world(db_session)

    run_prune(db_session, "tr")

    assert _vectors(db_session, "de") == 2
    (german,) = embedding_tasks(db_session)
    assert german.status is WorkTaskStatus.PENDING


def test_pruning_a_locale_without_vectors_reports_nothing_reclaimed(db_session: Session) -> None:
    _world(db_session)

    assert run_prune(db_session, "ro") == PruneReport("ro", vectors=0, tasks=0, bytes_reclaimed=0)
    assert _vectors(db_session, "de") == 2


def test_prune_refuses_an_unsupported_locale_and_deletes_nothing(db_session: Session) -> None:
    _world(db_session)

    with pytest.raises(SystemExit):
        _parse_options(["--locale", "xx"])

    assert _vectors(db_session, "tr") == 2
