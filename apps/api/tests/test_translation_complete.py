"""Validation order and outcomes of completing translation tasks (chapter 14)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

import pytest
from app.config import settings
from app.db import engine as db_engine
from app.features.translation.service import TranslationCompletion
from app.features.translation.store import TranslationPayload, TranslationStore
from app.models.api_key import ApiKey
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from app.schema.translation.machine import TranslationCompleteItem, TranslationItemResult, TranslationOutcome
from app.shared.object_store import InMemoryObjectStore, ObjectStore, ObjectStoreQuotaError
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from embedding_support import CommittedWorld
from translation_support import (
    NOW,
    claimed_by,
    complete_item,
    enqueuer,
    human_row,
    make_key,
    queued_task,
    stored_row,
    task_rows,
    unit_candidate,
    unit_hash,
)

Subscriber = Callable[[UUID, str, TranslationPayload], None]


class UnavailableStore(InMemoryObjectStore):
    """A store whose writes fail the way an unreachable or capped R2 does."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        raise ObjectStoreQuotaError("Monthly r2_class_a budget is exhausted")


class UntouchableStore(InMemoryObjectStore):
    """A store that fails the test when anything reaches it."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        raise AssertionError("put")

    def delete(self, key: str) -> None:
        raise AssertionError("delete")


class DeleteFails(InMemoryObjectStore):
    """A store whose deletes fail."""

    def delete(self, key: str) -> None:
        raise ObjectStoreQuotaError("Monthly r2_class_a budget is exhausted")


def _complete(
    session: Session,
    key: ApiKey,
    *items: TranslationCompleteItem,
    store: ObjectStore | None = None,
    subscribers: tuple[Subscriber, ...] = (),
) -> list[TranslationItemResult]:
    completion = TranslationCompletion(session, store, clock=lambda: NOW, subscribers=subscribers)
    return completion.complete(key.id, list(items))


def _claimed(session: Session, locale: str = "en") -> tuple[DiscoveryDocumentCandidate, TranslationTask, ApiKey]:
    candidate, task = queued_task(session, locale)
    key = make_key(session)
    claimed_by(session, task, key)
    return candidate, task, key


def _rows(session: Session) -> list[CandidateTranslation]:
    return list(session.scalars(select(CandidateTranslation)))


def test_complete_writes_the_object_then_the_index_row_and_completes_the_task(db_session: Session) -> None:
    candidate, task, key = _claimed(db_session)
    backend = InMemoryObjectStore()
    seen: list[tuple[UUID, str, TranslationPayload]] = []

    (result,) = _complete(
        db_session, key, complete_item(task, db_session), store=backend, subscribers=(lambda *args: seen.append(args),)
    )

    (row,) = _rows(db_session)
    payload = TranslationStore(backend).read(row.storage_key)
    assert (result.outcome, result.reason) == (TranslationOutcome.STORED, None)
    assert (row.candidate_id, row.locale, row.source, row.engine, row.model) == (
        candidate.id,
        "en",
        TranslationSource.MT,
        "llm",
        "qwen",
    )
    assert (row.source_hash, row.size_bytes) == (unit_hash(db_session, candidate), len(backend.get(row.storage_key)))
    assert (payload.title, payload.description, payload.source) == (
        "Child benefit application",
        "Please bring your ID",
        TranslationSource.MT,
    )
    assert (task.status, task.lease_expires_at) == (WorkTaskStatus.COMPLETED, None)
    assert seen == [(candidate.id, "en", payload)]


def test_a_stale_hash_is_discarded_requeued_and_costs_no_object_store_operation(db_session: Session) -> None:
    candidate, task, key = _claimed(db_session)
    old = unit_hash(db_session, candidate)
    candidate.title_i18n = {"de": "Geändert"}
    db_session.flush()

    (result,) = _complete(db_session, key, complete_item(task, db_session, source_hash=old), store=UntouchableStore())

    assert result.outcome is TranslationOutcome.STALE
    assert _rows(db_session) == []
    assert task.status is WorkTaskStatus.COMPLETED
    (fresh,) = task_rows(db_session, WorkTaskStatus.PENDING)
    assert (fresh.candidate_id, fresh.locale, fresh.source_hash) == (
        candidate.id,
        "en",
        unit_hash(db_session, candidate),
    )


def test_a_hash_the_task_was_not_leased_for_is_stale_even_when_it_is_current(db_session: Session) -> None:
    candidate, task, key = _claimed(db_session)
    task.source_hash = "leased-for-something-else"
    db_session.flush()

    (result,) = _complete(db_session, key, complete_item(task, db_session), store=UntouchableStore())

    assert result.outcome is TranslationOutcome.STALE
    assert _rows(db_session) == []


def test_a_human_translation_is_never_overwritten_and_touches_no_object(db_session: Session) -> None:
    candidate, task, key = _claimed(db_session)
    human = human_row(db_session, candidate, "en")

    (result,) = _complete(db_session, key, complete_item(task, db_session), store=UntouchableStore())

    assert (result.outcome, result.reason) == (TranslationOutcome.REJECTED, "human_exists")
    assert (_rows(db_session), human.source, human.storage_key) == ([human], TranslationSource.HUMAN, "k/human.json")
    assert task.status is WorkTaskStatus.COMPLETED


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "x" * 301}, "300"),
        ({"description": "y" * 4001}, "4000"),
        ({"title": "Ti\x00tle"}, "control"),
        ({"description": "Be\x07ll"}, "control"),
    ],
)
def test_empty_over_long_or_control_character_text_is_rejected_and_the_task_failed_without_a_write(
    db_session: Session, override: dict[str, object], reason: str
) -> None:
    _, task, key = _claimed(db_session)

    (result,) = _complete(db_session, key, complete_item(task, db_session, **override), store=UntouchableStore())

    assert result.outcome is TranslationOutcome.REJECTED
    assert result.reason is not None and reason in result.reason
    assert _rows(db_session) == []
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, result.reason)


def test_the_text_at_the_bounds_is_stored_trimmed(db_session: Session) -> None:
    _, task, key = _claimed(db_session)
    backend = InMemoryObjectStore()

    (result,) = _complete(
        db_session,
        key,
        complete_item(task, db_session, title=f"  {'t' * 300}  ", description="d" * 4000),
        store=backend,
    )

    (row,) = _rows(db_session)
    payload = TranslationStore(backend).read(row.storage_key)
    assert result.outcome is TranslationOutcome.STORED
    assert (len(payload.title), len(payload.description)) == (300, 4000)


def test_one_bad_item_never_fails_the_others(db_session: Session) -> None:
    (_, good_a, key), (_, bad, _), (_, good_c, _) = (_claimed(db_session) for _ in range(3))
    for task in (bad, good_c):
        claimed_by(db_session, task, key)
    backend = InMemoryObjectStore()

    results = _complete(
        db_session,
        key,
        complete_item(good_a, db_session),
        complete_item(bad, db_session, title=""),
        complete_item(good_c, db_session),
        store=backend,
    )

    assert [result.outcome for result in results] == [
        TranslationOutcome.STORED,
        TranslationOutcome.REJECTED,
        TranslationOutcome.STORED,
    ]
    assert len(_rows(db_session)) == 2


def test_a_task_claimed_by_another_key_is_rejected_and_left_alone(db_session: Session) -> None:
    _, task, owner = _claimed(db_session)
    intruder = make_key(db_session, "intruder")

    (result,) = _complete(db_session, intruder, complete_item(task, db_session), store=UntouchableStore())

    assert result.outcome is TranslationOutcome.REJECTED
    assert (task.status, task.claimed_by_api_key_id) == (WorkTaskStatus.CLAIMED, owner.id)


def test_an_unknown_task_and_a_pending_task_are_rejected(db_session: Session) -> None:
    _, pending = queued_task(db_session)
    key = make_key(db_session)
    unknown = TranslationCompleteItem(
        task_id=uuid.uuid4(), source_hash="h", title="t", description="d", engine="llm", model="m"
    )

    results = _complete(db_session, key, unknown, complete_item(pending, db_session), store=UntouchableStore())

    assert [result.outcome for result in results] == [TranslationOutcome.REJECTED] * 2
    assert pending.status is WorkTaskStatus.PENDING


def test_completing_the_same_task_twice_stores_once_and_rejects_the_repeat(db_session: Session) -> None:
    _, task, key = _claimed(db_session)
    item = complete_item(task, db_session)

    results = _complete(db_session, key, item, item, store=InMemoryObjectStore())

    assert [result.outcome for result in results] == [TranslationOutcome.STORED, TranslationOutcome.REJECTED]
    assert len(_rows(db_session)) == 1


def test_replacing_a_stale_translation_moves_the_index_row_and_deletes_the_old_object(db_session: Session) -> None:
    candidate = unit_candidate(db_session)
    backend = InMemoryObjectStore()
    backend.put("k/old.json", b"{}", "application/json")
    old = stored_row(db_session, candidate, "en", "old-hash", key="k/old.json")
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    (task,) = task_rows(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    _complete(db_session, key, complete_item(task, db_session), store=backend)
    db_session.commit()

    (row,) = _rows(db_session)
    assert row is old and row.storage_key != "k/old.json"
    assert row.source_hash == unit_hash(db_session, candidate)
    assert backend.stored_keys() == [row.storage_key]


def test_a_failing_delete_of_the_replaced_object_does_not_fail_the_item(db_session: Session) -> None:
    candidate = unit_candidate(db_session)
    backend = DeleteFails()
    backend.put("k/old.json", b"{}", "application/json")
    stored_row(db_session, candidate, "en", "old-hash", key="k/old.json")
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    (task,) = task_rows(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    (result,) = _complete(db_session, key, complete_item(task, db_session), store=backend)
    db_session.commit()

    assert result.outcome is TranslationOutcome.STORED
    assert task.status is WorkTaskStatus.COMPLETED
    assert "k/old.json" in backend.stored_keys()


def test_the_replaced_object_is_not_deleted_when_the_transaction_rolls_back(db_session: Session) -> None:
    candidate = unit_candidate(db_session)
    backend = InMemoryObjectStore()
    backend.put("k/old.json", b"{}", "application/json")
    stored_row(db_session, candidate, "en", "old-hash", key="k/old.json")
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    (task,) = task_rows(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    _complete(db_session, key, complete_item(task, db_session), store=backend)
    db_session.rollback()

    assert "k/old.json" in backend.stored_keys()


def test_identical_text_replacing_itself_keeps_its_object(db_session: Session) -> None:
    candidate, task, key = _claimed(db_session)
    backend = InMemoryObjectStore()
    _complete(db_session, key, complete_item(task, db_session), store=backend)
    db_session.commit()
    (first,) = _rows(db_session)
    kept = first.storage_key
    db_session.execute(text("UPDATE candidate_translation SET source_hash = 'older'"))
    db_session.expire_all()
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    (again,) = task_rows(db_session, WorkTaskStatus.PENDING)
    claimed_by(db_session, again, key)

    _complete(db_session, key, complete_item(again, db_session), store=backend)
    db_session.commit()

    assert backend.stored_keys() == [kept]
    assert _rows(db_session)[0].source_hash == unit_hash(db_session, candidate)


@pytest.mark.parametrize("store", [None, UnavailableStore()], ids=["not configured", "over the cap or erroring"])
def test_an_unavailable_object_store_hands_the_task_back_without_an_index_row_or_a_burned_attempt(
    db_session: Session, store: ObjectStore | None
) -> None:
    _, task, key = _claimed(db_session)

    (result,) = _complete(db_session, key, complete_item(task, db_session), store=store)

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert _rows(db_session) == []
    assert (task.status, task.attempt_count, task.claimed_by_api_key_id) == (WorkTaskStatus.PENDING, 0, None)
    assert task.last_error is not None


def test_an_unavailable_store_does_not_spoil_stale_and_rejected_items_of_the_same_batch(db_session: Session) -> None:
    (_, unavailable, key), (_, bad, _) = _claimed(db_session), _claimed(db_session)
    claimed_by(db_session, bad, key)

    results = _complete(
        db_session,
        key,
        complete_item(unavailable, db_session),
        complete_item(bad, db_session, title=""),
        store=UnavailableStore(),
    )

    assert [result.outcome for result in results] == [TranslationOutcome.UNAVAILABLE, TranslationOutcome.REJECTED]


def test_a_failure_after_the_put_leaves_no_index_row_and_only_an_unreferenced_object(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, task, key = _claimed(db_session)
    backend = InMemoryObjectStore()
    from app.features.translation import service

    def explode(*_: object, **__: object) -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(service.TranslationRepository, "upsert_row", explode)

    with pytest.raises(RuntimeError):
        _complete(db_session, key, complete_item(task, db_session), store=backend)
    db_session.rollback()

    assert len(backend.stored_keys()) == 1
    assert _rows(db_session) == []


def test_a_failing_subscriber_does_not_lose_the_translation(db_session: Session) -> None:
    _, task, key = _claimed(db_session)

    def refuse(*_: object) -> None:
        raise RuntimeError("search refresh failed")

    (result,) = _complete(
        db_session, key, complete_item(task, db_session), store=InMemoryObjectStore(), subscribers=(refuse,)
    )

    assert result.outcome is TranslationOutcome.STORED
    assert len(_rows(db_session)) == 1
    assert task.status is WorkTaskStatus.COMPLETED


def test_a_worker_whose_lease_was_reclaimed_by_another_key_cannot_complete_the_task(db_session: Session) -> None:
    _, task, slow = _claimed(db_session)
    fast = make_key(db_session, "fast")
    from app.features.translation.queue import TranslationQueue

    later = TranslationQueue(db_session, clock=lambda: NOW + timedelta(minutes=16))
    (served,) = later.claim(fast.id, limit=1).items

    (late,) = _complete(db_session, slow, complete_item(task, db_session), store=UntouchableStore())
    (timely,) = _complete(db_session, fast, complete_item(task, db_session), store=InMemoryObjectStore())

    assert (served.task_id, late.outcome, timely.outcome) == (
        task.id,
        TranslationOutcome.REJECTED,
        TranslationOutcome.STORED,
    )


def test_the_check_of_the_current_unit_blocks_a_concurrent_rewrite_until_the_batch_settles(
    db_session: Session,
) -> None:
    """The share lock on the candidate stops a title change slipping between the hash check and the stored text."""
    world = CommittedWorld()
    with Session(bind=db_engine, expire_on_commit=False) as setup:
        candidate, task = queued_task(setup)
        key = make_key(setup)
        world.candidate_ids, world.key_ids = [candidate.id], [key.id]
        claimed_by(setup, task, key)
        setup.commit()
    try:
        with Session(bind=db_engine) as completing, Session(bind=db_engine) as rewriting:
            live = completing.get(TranslationTask, task.id)
            assert live is not None
            _complete(completing, key, complete_item(live, completing), store=InMemoryObjectStore())
            rewriting.execute(text("SET LOCAL lock_timeout = '300ms'"))

            with pytest.raises(OperationalError):
                rewriting.execute(
                    text("UPDATE discovery_document_candidate SET official_url = 'https://x.example' WHERE id = :id"),
                    {"id": candidate.id},
                )
            rewriting.rollback()
            completing.rollback()
    finally:
        _forget_committed(world)


def _forget_committed(world: CommittedWorld) -> None:
    from embedding_support import _forget

    with Session(bind=db_engine) as cleanup:
        _forget(cleanup, world)


def test_the_default_settings_name_the_locales_a_completion_may_store(db_session: Session) -> None:
    _, task, key = _claimed(db_session, "tr")

    (result,) = _complete(db_session, key, complete_item(task, db_session), store=InMemoryObjectStore())

    assert "tr" in settings.translation_target_locale_codes
    assert result.outcome is TranslationOutcome.STORED
