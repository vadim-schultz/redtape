"""Claim, lease, reclaim, fail, release and summary of the embedding task queue (chapter 5)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from app.db import engine as db_engine
from app.features.discovery.task_retry import BACKOFF, MAX_ATTEMPTS
from app.features.search.errors import InvalidTaskMoveError, TaskNotOwnedError
from app.features.search.queue import EmbeddingQueue
from app.features.search.task_states import can_move, move
from app.models.search import CandidateSearchText, WorkTaskStatus
from app.schema.search.machine import EmbeddingFailRequest
from sqlalchemy import text
from sqlalchemy.orm import Session

from embedding_support import MODEL, NOW, claimed_by, committed_world, current_hash, make_key, queued

LATER = NOW + timedelta(minutes=16)


def _queue(session: Session) -> EmbeddingQueue:
    return EmbeddingQueue(session, clock=lambda: NOW)


def _fail(queue: EmbeddingQueue, key_id: uuid.UUID, task_id: uuid.UUID, error: str, *, retryable: bool) -> None:
    queue.fail(key_id, EmbeddingFailRequest(task_id=task_id, error=error, retryable=retryable))


def test_claim_leases_a_pending_task_with_its_current_text(db_session: Session) -> None:
    candidate, task = queued(db_session)
    key = make_key(db_session)

    (item,) = _queue(db_session).claim(key.id, MODEL, limit=5).items

    assert (item.task_id, item.candidate_id, item.locale) == (task.id, candidate.id, "de")
    assert item.text == "Kindergeldantrag"
    assert item.text_hash == current_hash(db_session, task)
    assert item.lease_expires_at == NOW + timedelta(minutes=15)
    assert (task.status, task.attempt_count, task.claimed_by_api_key_id) == (WorkTaskStatus.CLAIMED, 1, key.id)


def test_claim_of_another_model_leases_nothing(db_session: Session) -> None:
    _, task = queued(db_session)

    assert _queue(db_session).claim(make_key(db_session).id, "other-model", limit=5).items == []
    assert task.status is WorkTaskStatus.PENDING


def test_claim_serves_the_current_hash_when_the_task_carries_an_older_one(db_session: Session) -> None:
    _, task = queued(db_session)
    task.text_hash = "old"
    db_session.flush()

    (item,) = _queue(db_session).claim(make_key(db_session).id, MODEL, limit=5).items

    assert item.text_hash == current_hash(db_session, task)
    assert task.text_hash == item.text_hash


def test_claim_fails_a_task_whose_search_text_is_gone_and_does_not_serve_it(db_session: Session) -> None:
    candidate, task = queued(db_session)
    db_session.delete(db_session.get(CandidateSearchText, (candidate.id, "de")))
    db_session.flush()

    assert _queue(db_session).claim(make_key(db_session).id, MODEL, limit=5).items == []
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, "search text missing")


def test_claim_orders_by_priority_then_age_then_id_and_honours_the_limit(db_session: Session) -> None:
    (_, old), (_, new), (_, urgent) = (queued(db_session, f"Antrag {n}") for n in range(3))
    old.created_at, new.created_at = NOW - timedelta(hours=2), NOW - timedelta(hours=1)
    urgent.created_at, urgent.priority = NOW, 10
    db_session.flush()

    items = _queue(db_session).claim(make_key(db_session).id, MODEL, limit=2).items

    assert [item.task_id for item in items] == [urgent.id, old.id]
    assert new.status is WorkTaskStatus.PENDING


def test_claim_skips_a_task_held_back_by_not_before_until_it_is_due(db_session: Session) -> None:
    _, task = queued(db_session)
    task.not_before = NOW + timedelta(minutes=5)
    db_session.flush()

    assert _queue(db_session).claim(make_key(db_session).id, MODEL, limit=5).items == []
    later = EmbeddingQueue(db_session, clock=lambda: NOW + timedelta(minutes=5))
    assert [item.task_id for item in later.claim(make_key(db_session).id, MODEL, limit=5).items] == [task.id]


def test_claim_reclaims_an_expired_lease_for_a_new_key(db_session: Session) -> None:
    _, task = queued(db_session)
    first, second = make_key(db_session, "a"), make_key(db_session, "b")
    claimed_by(db_session, task, first)

    reclaimed = EmbeddingQueue(db_session, clock=lambda: LATER).claim(second.id, MODEL, limit=5).items

    assert [item.task_id for item in reclaimed] == [task.id]
    assert (task.claimed_by_api_key_id, task.attempt_count) == (second.id, 2)


def test_claim_leaves_a_live_lease_alone(db_session: Session) -> None:
    _, task = queued(db_session)
    first = make_key(db_session, "a")
    claimed_by(db_session, task, first)

    assert _queue(db_session).claim(make_key(db_session, "b").id, MODEL, limit=5).items == []
    assert task.claimed_by_api_key_id == first.id


def test_claim_fails_an_expired_lease_that_used_every_attempt(db_session: Session) -> None:
    _, task = queued(db_session)
    claimed_by(db_session, task, make_key(db_session), attempts=MAX_ATTEMPTS)

    items = EmbeddingQueue(db_session, clock=lambda: LATER).claim(make_key(db_session, "b").id, MODEL, limit=5).items

    assert items == []
    assert task.status is WorkTaskStatus.FAILED
    assert task.last_error == f"lease expired after {MAX_ATTEMPTS} attempts"


def test_a_retryable_failure_backs_off_and_stops_at_the_attempt_cap(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    queue = _queue(db_session)
    for attempt in range(1, MAX_ATTEMPTS):
        claimed_by(db_session, task, key, attempts=attempt)
        _fail(queue, key.id, task.id, "boom", retryable=True)
        assert (task.status, task.not_before) == (WorkTaskStatus.PENDING, NOW + BACKOFF[attempt - 1])
        assert task.claimed_by_api_key_id is None
    claimed_by(db_session, task, key, attempts=MAX_ATTEMPTS)

    _fail(queue, key.id, task.id, "boom", retryable=True)

    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, "boom")


def test_a_non_retryable_failure_fails_the_task_at_once(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    _fail(_queue(db_session), key.id, task.id, "bad text", retryable=False)

    assert (task.status, task.last_error, task.lease_expires_at) == (WorkTaskStatus.FAILED, "bad text", None)


def test_fail_by_a_key_that_does_not_hold_the_lease_is_refused_and_changes_nothing(db_session: Session) -> None:
    _, task = queued(db_session)
    claimed_by(db_session, task, make_key(db_session, "owner"))
    intruder = make_key(db_session, "intruder")

    with pytest.raises(TaskNotOwnedError):
        _fail(_queue(db_session), intruder.id, task.id, "boom", retryable=False)
    with pytest.raises(TaskNotOwnedError):
        _fail(_queue(db_session), intruder.id, uuid.uuid4(), "boom", retryable=False)

    assert (task.status, task.last_error) == (WorkTaskStatus.CLAIMED, None)


def test_release_returns_tasks_to_pending_without_consuming_an_attempt(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key, attempts=2)

    result = _queue(db_session).release(key.id, [task.id], "neuron_quota")

    assert result.released == [task.id]
    assert (task.status, task.attempt_count, task.last_error) == (WorkTaskStatus.PENDING, 1, "neuron_quota")
    assert (task.claimed_by_api_key_id, task.lease_expires_at) == (None, None)


def test_release_skips_tasks_the_key_does_not_hold_and_still_releases_the_rest(db_session: Session) -> None:
    (_, mine), (_, theirs) = queued(db_session, "Meins"), queued(db_session, "Deins")
    key, other = make_key(db_session, "me"), make_key(db_session, "other")
    claimed_by(db_session, mine, key)
    claimed_by(db_session, theirs, other)

    result = _queue(db_session).release(key.id, [mine.id, theirs.id, uuid.uuid4()], "neuron_quota")

    assert result.released == [mine.id]
    assert len(result.skipped) == 2
    assert (mine.status, theirs.status) == (WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED)


def test_release_of_a_repeated_id_hands_the_task_back_once(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key, attempts=1)

    result = _queue(db_session).release(key.id, [task.id, task.id], "neuron_quota")

    assert (result.released, result.skipped) == ([task.id], [])
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)


def test_summary_counts_ready_claimed_failed_and_stale_candidates(db_session: Session) -> None:
    (_, ready), (_, delayed), (_, held), (_, failed) = (queued(db_session, f"Antrag {n}") for n in range(4))
    delayed.not_before = NOW + timedelta(hours=1)
    claimed_by(db_session, held, make_key(db_session))
    failed.status = WorkTaskStatus.FAILED
    db_session.flush()

    summary = _queue(db_session).summary(MODEL)

    assert (summary.pending_ready, summary.claimed, summary.failed) == (1, 1, 1)
    assert summary.stale_candidates == 4
    assert ready.status is WorkTaskStatus.PENDING


def test_summary_reports_the_oldest_ready_age_and_the_24_hour_finished_counts(db_session: Session) -> None:
    """stats · the oldest ready task sets the age; a task finished 25 h ago is not in the 24 h counts."""
    (_, old), (_, recent_done), (_, old_done), (_, recent_failed) = (
        queued(db_session, f"Antrag {n}") for n in range(4)
    )
    old.created_at = NOW - timedelta(hours=3)
    recent_done.status = WorkTaskStatus.COMPLETED
    recent_done.updated_at = NOW - timedelta(hours=1)
    old_done.status = WorkTaskStatus.COMPLETED
    old_done.updated_at = NOW - timedelta(hours=25)
    recent_failed.status = WorkTaskStatus.FAILED
    recent_failed.updated_at = NOW - timedelta(hours=2)
    db_session.flush()

    summary = _queue(db_session).summary(MODEL)

    assert summary.oldest_pending_age_seconds == 3 * 3600
    assert (summary.completed_24h, summary.failed_24h) == (1, 1)


def test_summary_of_an_empty_queue_is_all_zero(db_session: Session) -> None:
    summary = _queue(db_session).summary(MODEL)

    assert summary.model_dump() == {"pending_ready": 0, "claimed": 0, "failed": 0, "stale_candidates": 0}


def test_two_concurrent_claimers_never_receive_the_same_task(db_session: Session) -> None:
    """Both claims run in open transactions on their own connections; ``SKIP LOCKED`` keeps them apart."""
    with committed_world(tasks=6) as (world, (key_a, key_b)):
        with Session(bind=db_engine) as first, Session(bind=db_engine) as second:
            second.execute(text("SET LOCAL lock_timeout = '3s'"))
            from_a = EmbeddingQueue(first, clock=lambda: NOW).claim(key_a.id, MODEL, limit=3).items
            from_b = EmbeddingQueue(second, clock=lambda: NOW).claim(key_b.id, MODEL, limit=3).items
            first.commit()
            second.commit()

        ids_a, ids_b = {item.task_id for item in from_a}, {item.task_id for item in from_b}
        assert len(ids_a) == len(ids_b) == 3
        assert ids_a.isdisjoint(ids_b)
        assert ids_a | ids_b == set(world.task_ids)


def test_a_claim_committed_by_one_session_is_not_claimable_again(db_session: Session) -> None:
    with committed_world(tasks=2) as (world, (key_a, key_b)):
        with Session(bind=db_engine) as first:
            EmbeddingQueue(first, clock=lambda: NOW).claim(key_a.id, MODEL, limit=2)
            first.commit()
        with Session(bind=db_engine) as second:
            again = EmbeddingQueue(second, clock=lambda: NOW).claim(key_b.id, MODEL, limit=2).items

        assert again == []
        assert len(world.task_ids) == 2


def test_the_status_table_allows_only_the_documented_moves() -> None:
    allowed = {(WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED)} | {
        (WorkTaskStatus.CLAIMED, target)
        for target in (WorkTaskStatus.PENDING, WorkTaskStatus.COMPLETED, WorkTaskStatus.FAILED)
    }
    every = {(source, target) for source in WorkTaskStatus for target in WorkTaskStatus}

    assert {pair for pair in every if can_move(*pair)} == allowed


def test_a_task_cannot_leave_a_final_status(db_session: Session) -> None:
    _, task = queued(db_session)
    task.status = WorkTaskStatus.COMPLETED

    with pytest.raises(InvalidTaskMoveError):
        move(task, WorkTaskStatus.CLAIMED)
    assert task.status is WorkTaskStatus.COMPLETED
