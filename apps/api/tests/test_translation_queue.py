"""Claim, lease, fail and release of the translation task queue on the shared leased queue (chapter 14)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

import pytest
from app.config import settings
from app.db import engine as db_engine
from app.features.discovery.task_retry import BACKOFF, MAX_ATTEMPTS
from app.features.search.errors import TaskNotOwnedError
from app.features.translation.queue import TranslationQueue
from app.models.search import WorkTaskStatus
from app.schema.translation.machine import TranslationFailRequest
from sqlalchemy import text
from sqlalchemy.orm import Session

from embedding_support import CommittedWorld, _forget
from translation_support import NOW, claimed_by, enqueuer, make_key, queued_task, unit_candidate, unit_hash

LATER = NOW + timedelta(minutes=16)


def _queue(session: Session) -> TranslationQueue:
    return TranslationQueue(session, clock=lambda: NOW)


def _fail(queue: TranslationQueue, key_id: uuid.UUID, task_id: uuid.UUID, *, retryable: bool) -> None:
    queue.fail(key_id, TranslationFailRequest(task_id=task_id, error="boom", retryable=retryable))


def test_claim_leases_a_pending_task_with_its_current_unit(db_session: Session) -> None:
    candidate, task = queued_task(db_session)
    key = make_key(db_session)

    (item,) = _queue(db_session).claim(key.id, limit=5).items

    assert (item.task_id, item.candidate_id, item.locale, item.source_locale) == (task.id, candidate.id, "en", "de")
    assert (item.title, item.description) == ("Kindergeldantrag", "Bitte Ausweis mitbringen")
    assert item.source_hash == task.source_hash == unit_hash(db_session, candidate)
    assert item.lease_expires_at == NOW + timedelta(minutes=15)
    assert (task.status, task.attempt_count, task.claimed_by_api_key_id) == (WorkTaskStatus.CLAIMED, 1, key.id)


def test_claim_serves_the_current_hash_when_the_task_carries_an_older_one(db_session: Session) -> None:
    candidate, task = queued_task(db_session)
    task.source_hash = "old"
    db_session.flush()

    (item,) = _queue(db_session).claim(make_key(db_session).id, limit=5).items

    assert item.source_hash == unit_hash(db_session, candidate)
    assert task.source_hash == item.source_hash


def test_claim_fails_a_task_whose_german_source_is_gone_and_does_not_serve_it(db_session: Session) -> None:
    candidate, task = queued_task(db_session)
    candidate.title_i18n = {}
    db_session.flush()

    items = _queue(db_session).claim(make_key(db_session).id, limit=5).items

    assert items == []
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, "german source missing")


def test_claim_leaves_a_locale_that_is_no_longer_a_target_in_the_queue(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, english = queued_task(db_session, "en")
    _, turkish = queued_task(db_session, "tr")
    monkeypatch.setattr(settings, "translation_target_locales", "tr")

    items = _queue(db_session).claim(make_key(db_session).id, limit=5).items

    assert [item.task_id for item in items] == [turkish.id]
    assert english.status is WorkTaskStatus.PENDING


def test_claim_with_translation_switched_off_leases_nothing(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, task = queued_task(db_session)
    monkeypatch.setattr(settings, "translation_target_locales", "")

    assert _queue(db_session).claim(make_key(db_session).id, limit=5).items == []
    assert task.status is WorkTaskStatus.PENDING


def test_claim_skips_a_task_held_back_by_not_before_until_it_is_due(db_session: Session) -> None:
    _, task = queued_task(db_session)
    task.not_before = NOW + timedelta(hours=1)
    db_session.flush()
    key = make_key(db_session)

    early = _queue(db_session).claim(key.id, limit=5).items
    due = TranslationQueue(db_session, clock=lambda: NOW + timedelta(hours=2)).claim(key.id, limit=5).items

    assert (early, [item.task_id for item in due]) == ([], [task.id])


def test_claim_reclaims_an_expired_lease_for_a_new_key_and_leaves_a_live_lease_alone(db_session: Session) -> None:
    _, task = queued_task(db_session)
    slow, fast = make_key(db_session, "slow"), make_key(db_session, "fast")
    claimed_by(db_session, task, slow)

    live = _queue(db_session).claim(fast.id, limit=5).items
    reclaimed = TranslationQueue(db_session, clock=lambda: LATER).claim(fast.id, limit=5).items

    assert (live, [item.task_id for item in reclaimed]) == ([], [task.id])
    assert task.claimed_by_api_key_id == fast.id


def test_a_retryable_failure_backs_off_and_stops_at_the_attempt_cap(db_session: Session) -> None:
    _, task = queued_task(db_session)
    key = make_key(db_session)
    queue = _queue(db_session)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        task.not_before = None
        (served,) = queue.claim(key.id, limit=1).items
        _fail(queue, key.id, served.task_id, retryable=True)
        if attempt < MAX_ATTEMPTS:
            assert (task.status, task.not_before) == (WorkTaskStatus.PENDING, NOW + BACKOFF[attempt - 1])

    assert (task.status, task.attempt_count, task.last_error) == (WorkTaskStatus.FAILED, MAX_ATTEMPTS, "boom")


def test_a_non_retryable_failure_fails_the_task_at_once(db_session: Session) -> None:
    _, task = queued_task(db_session)
    key = make_key(db_session)
    queue = _queue(db_session)
    queue.claim(key.id, limit=1)

    _fail(queue, key.id, task.id, retryable=False)

    assert (task.status, task.attempt_count) == (WorkTaskStatus.FAILED, 1)


def test_fail_by_a_key_that_does_not_hold_the_lease_is_refused_and_changes_nothing(db_session: Session) -> None:
    _, task = queued_task(db_session)
    owner, intruder = make_key(db_session, "owner"), make_key(db_session, "intruder")
    claimed_by(db_session, task, owner)

    with pytest.raises(TaskNotOwnedError):
        _fail(_queue(db_session), intruder.id, task.id, retryable=False)

    assert (task.status, task.claimed_by_api_key_id) == (WorkTaskStatus.CLAIMED, owner.id)


def test_release_returns_tasks_without_consuming_an_attempt_and_skips_those_the_key_does_not_hold(
    db_session: Session,
) -> None:
    _, mine = queued_task(db_session)
    _, theirs = queued_task(db_session, title="Anderer")
    key, other = make_key(db_session), make_key(db_session, "other")
    claimed_by(db_session, mine, key)
    claimed_by(db_session, theirs, other)

    response = _queue(db_session).release(key.id, [mine.id, theirs.id, mine.id], "budget")

    assert (response.released, response.skipped) == ([mine.id], [theirs.id])
    assert (mine.status, mine.attempt_count, mine.last_error) == (WorkTaskStatus.PENDING, 0, "budget")
    assert theirs.status is WorkTaskStatus.CLAIMED


def test_summary_of_an_empty_queue_is_zero_for_every_target_locale(db_session: Session) -> None:
    summary = _queue(db_session).summary()

    assert [entry.locale for entry in summary.locales] == list(settings.translation_target_locale_codes)
    assert all(
        entry.pending_ready == entry.claimed == entry.failed == entry.translated == 0 for entry in summary.locales
    )


@contextmanager
def _committed_candidates(count: int) -> Iterator[tuple[CommittedWorld, list[uuid.UUID]]]:
    world = CommittedWorld()
    with Session(bind=db_engine, expire_on_commit=False) as session:
        made = [unit_candidate(session, f"Committed Antrag {n}") for n in range(count)]
        enqueuer(session, ("en",)).enqueue_many([candidate.id for candidate in made])
        keys = [make_key(session, f"committed-{n}") for n in range(2)]
        world.candidate_ids, world.key_ids = [candidate.id for candidate in made], [key.id for key in keys]
        session.commit()
        try:
            yield world, world.key_ids
        finally:
            session.rollback()
            _forget(session, world)


def test_two_concurrent_claimers_never_receive_the_same_task(db_session: Session) -> None:
    """Both claims run in open transactions on their own connections; ``SKIP LOCKED`` keeps them apart."""
    with _committed_candidates(6) as (world, (key_a, key_b)):
        with Session(bind=db_engine) as first, Session(bind=db_engine) as second:
            second.execute(text("SET LOCAL lock_timeout = '3s'"))
            from_a = TranslationQueue(first, clock=lambda: NOW).claim(key_a, limit=3).items
            from_b = TranslationQueue(second, clock=lambda: NOW).claim(key_b, limit=3).items
            first.commit()
            second.commit()

        ids_a, ids_b = {item.task_id for item in from_a}, {item.task_id for item in from_b}
        assert len(ids_a) == len(ids_b) == 3
        assert ids_a.isdisjoint(ids_b)
        assert {item.candidate_id for item in from_a + from_b} == set(world.candidate_ids)


def test_a_claim_committed_by_one_session_is_not_claimable_again() -> None:
    with _committed_candidates(2) as (_, (key_a, key_b)):
        with Session(bind=db_engine) as first:
            TranslationQueue(first, clock=lambda: NOW).claim(key_a, limit=2)
            first.commit()
        with Session(bind=db_engine) as second:
            again = TranslationQueue(second, clock=lambda: NOW).claim(key_b, limit=2).items

        assert again == []
