"""Refreshing search text and enqueueing embedding work (chapter 4), directly and through the write hook."""

from __future__ import annotations

import uuid

from app.features.search.hashing import content_hash
from app.features.search.service import RefreshStatus
from app.models.search import CandidateSearchText, EmbeddingTask
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from search_support import make_candidate, make_mention, open_tasks, search_service
from test_discovery_admin_api import _catalogue
from test_discovery_candidates_api import _item, _post
from test_discovery_machine_api import _issue_key, client  # noqa: F401


def _row(session: Session, candidate_id: object) -> CandidateSearchText:
    return session.scalars(select(CandidateSearchText).where(CandidateSearchText.candidate_id == candidate_id)).one()


def _xmin(session: Session) -> str:
    return str(session.scalar(text("select xmin::text from candidate_search_text")))


def test_refresh_writes_the_row_and_queues_one_task_with_its_hash(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    make_mention(db_session, candidate, "Elterngeld beantragen", score=0.9)

    result = search_service(db_session).refresh(candidate.id)

    row = _row(db_session, candidate.id)
    (task,) = open_tasks(db_session)
    assert (result.status, result.enqueued) == (RefreshStatus.WRITTEN, True)
    assert (row.locale, row.text) == ("de", "Kindergeldantrag Elterngeld beantragen")
    assert row.content_hash == content_hash(row.text) == task.text_hash


def test_a_new_mention_changes_the_hash_and_leaves_exactly_one_task_with_the_new_hash(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    service = search_service(db_session)
    service.refresh(candidate.id)
    old_hash = _row(db_session, candidate.id).content_hash

    make_mention(db_session, candidate, "Bitte Geburtsurkunde mitbringen", score=0.8)
    result = service.refresh(candidate.id)

    row = _row(db_session, candidate.id)
    (task,) = open_tasks(db_session)
    assert result.status is RefreshStatus.WRITTEN
    assert row.content_hash != old_hash
    assert task.text_hash == row.content_hash


def test_an_unchanged_text_does_not_rewrite_the_row_or_enqueue(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    service = search_service(db_session)
    service.refresh(candidate.id)
    version = _xmin(db_session)
    task_version = [(task.id, task.updated_at) for task in open_tasks(db_session)]

    result = service.refresh(candidate.id)

    assert (result.status, result.enqueued) == (RefreshStatus.UNCHANGED, False)
    assert _xmin(db_session) == version
    assert [(task.id, task.updated_at) for task in open_tasks(db_session)] == task_version


def test_an_empty_title_and_no_excerpts_produce_no_row_and_no_task(db_session: Session) -> None:
    candidate = make_candidate(db_session, title="")

    result = search_service(db_session).refresh(candidate.id)

    assert (result.status, result.enqueued) == (RefreshStatus.SKIPPED_EMPTY, False)
    assert db_session.scalar(select(func.count()).select_from(CandidateSearchText)) == 0
    assert db_session.scalar(select(func.count()).select_from(EmbeddingTask)) == 0


def test_an_unknown_candidate_is_skipped_without_writing(db_session: Session) -> None:
    result = search_service(db_session).refresh(uuid.uuid4())

    assert result.status is RefreshStatus.SKIPPED_EMPTY
    assert db_session.scalar(select(func.count()).select_from(CandidateSearchText)) == 0


def test_refresh_many_totals_every_outcome(db_session: Session) -> None:
    first, second = make_candidate(db_session), make_candidate(db_session, title="")
    service = search_service(db_session)
    service.refresh(first.id)

    totals = service.refresh_many([first.id, second.id, make_candidate(db_session).id])

    assert (totals.written, totals.unchanged, totals.skipped_empty, totals.enqueued) == (1, 1, 1, 1)


def _matches(session: Session, column: str, config: str, query: str) -> bool:
    sql = f"select {column} @@ websearch_to_tsquery('{config}', unaccent(:q)) from candidate_search_text"
    return bool(session.scalar(text(sql), {"q": query}))


def test_tsvectors_match_german_stems_and_exact_tokens(db_session: Session) -> None:
    candidate = make_candidate(db_session, title="Kindergeldantrag")
    make_mention(db_session, candidate, "Elterngeld beantragen für Eltern", score=0.5)
    search_service(db_session).refresh(candidate.id)

    assert _matches(db_session, "tsv_native", "german", "Elterngelder") is True
    assert _matches(db_session, "tsv_native", "german", "Kindergeldanträge") is True
    assert _matches(db_session, "tsv_simple", "simple", "Kindergeldantrag") is True
    assert _matches(db_session, "tsv_simple", "simple", "Kindergeldanträge") is False
    assert _matches(db_session, "tsv_simple", "simple", "für") is True


def test_recording_a_mention_through_the_machine_route_refreshes_the_search_text(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    _post(client, key, _item(catalogue))

    row = db_session.scalars(select(CandidateSearchText)).one()
    (task,) = open_tasks(db_session)
    assert row.text == "Personalausweis Bitte bringen Sie Ihren Personalausweis mit."
    assert task.text_hash == row.content_hash


def test_a_changed_excerpt_updates_the_task_and_an_identical_replay_changes_nothing(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue))
    first_hash = db_session.scalars(select(CandidateSearchText)).one().content_hash

    _post(client, key, _item(catalogue))
    assert db_session.scalars(select(CandidateSearchText)).one().content_hash == first_hash

    _post(client, key, _item(catalogue, excerpt="Neuer Text"))
    row = db_session.scalars(select(CandidateSearchText)).one()
    (task,) = open_tasks(db_session)
    assert row.text.endswith("Neuer Text")
    assert task.text_hash == row.content_hash != first_hash
