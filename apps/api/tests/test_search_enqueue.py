"""Hash-aware, idempotent embedding enqueue (chapter 4)."""

from __future__ import annotations

from app.config import settings
from app.features.search.enqueue import EmbeddingEnqueuer, EnqueueOutcome
from app.features.search.hashing import content_hash
from app.features.search.text import BuiltText
from app.models.search import EmbeddingTask, WorkTaskStatus
from sqlalchemy.orm import Session

from search_support import embed, make_candidate, open_tasks


def _built(text: str) -> BuiltText:
    return BuiltText(locale="de", text=text, content_hash=content_hash(text))


def test_enqueue_inserts_one_pending_task_for_the_configured_model(db_session: Session) -> None:
    candidate = make_candidate(db_session)

    outcome = EmbeddingEnqueuer(db_session, settings.embedding_model).enqueue(candidate.id, _built("a"))

    (task,) = open_tasks(db_session)
    assert outcome is EnqueueOutcome.QUEUED
    assert (task.candidate_id, task.model, task.locale) == (candidate.id, settings.embedding_model, "de")
    assert (task.status, task.text_hash) == (WorkTaskStatus.PENDING, _built("a").content_hash)


def test_a_second_change_while_pending_updates_the_task_hash_not_a_second_task(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("a"))

    outcome = enqueuer.enqueue(candidate.id, _built("b"))

    (task,) = open_tasks(db_session)
    assert outcome is EnqueueOutcome.QUEUED
    assert task.text_hash == _built("b").content_hash


def test_repeating_the_same_hash_while_pending_leaves_the_task_alone(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("a"))

    assert enqueuer.enqueue(candidate.id, _built("a")) is EnqueueOutcome.LEFT_OPEN
    assert len(open_tasks(db_session)) == 1


def test_a_claimed_task_is_not_modified_by_a_text_change(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("a"))
    (task,) = open_tasks(db_session)
    task.status = WorkTaskStatus.CLAIMED
    db_session.flush()

    outcome = enqueuer.enqueue(candidate.id, _built("b"))
    db_session.refresh(task)

    assert outcome is EnqueueOutcome.LEFT_OPEN
    assert (task.status, task.text_hash) == (WorkTaskStatus.CLAIMED, _built("a").content_hash)
    assert len(open_tasks(db_session)) == 1


def test_a_finished_task_does_not_block_a_new_one(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("a"))
    open_tasks(db_session)[0].status = WorkTaskStatus.COMPLETED
    db_session.flush()

    assert enqueuer.enqueue(candidate.id, _built("b")) is EnqueueOutcome.QUEUED
    assert [task.status for task in open_tasks(db_session)].count(WorkTaskStatus.PENDING) == 1


def test_a_text_that_is_already_embedded_enqueues_nothing(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    embed(db_session, candidate, _built("a").content_hash)

    outcome = EmbeddingEnqueuer(db_session, settings.embedding_model).enqueue(candidate.id, _built("a"))

    assert outcome is EnqueueOutcome.CURRENT
    assert open_tasks(db_session) == []


def test_reverting_to_the_embedded_text_retires_the_stale_pending_task(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    embed(db_session, candidate, _built("a").content_hash)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("b"))

    outcome = enqueuer.enqueue(candidate.id, _built("a"))

    assert outcome is EnqueueOutcome.CURRENT
    assert open_tasks(db_session) == []


def test_reverting_does_not_touch_a_claimed_task(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    embed(db_session, candidate, _built("a").content_hash)
    enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
    enqueuer.enqueue(candidate.id, _built("b"))
    (task,) = open_tasks(db_session)
    task.status = WorkTaskStatus.CLAIMED
    db_session.flush()

    enqueuer.enqueue(candidate.id, _built("a"))

    assert [t.status for t in db_session.query(EmbeddingTask).all()] == [WorkTaskStatus.CLAIMED]
