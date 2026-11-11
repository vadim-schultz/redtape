"""Validation order and outcomes of completing embedding tasks (chapter 5)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from app.db import engine as db_engine
from app.features.search.complete import EmbeddingCompletion
from app.features.search.enqueue import EmbeddingEnqueuer
from app.features.search.queue import EmbeddingQueue
from app.features.search.text import BuiltText
from app.models.api_key import ApiKey
from app.models.search import EMBEDDING_DIM, CandidateEmbedding, CandidateSearchText, EmbeddingTask, WorkTaskStatus
from app.schema.search.machine import EmbeddingCompleteItem, EmbeddingItemResult, EmbeddingOutcome
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from embedding_support import MODEL, NOW, claimed_by, committed_world, current_hash, make_key, queued, unit_vector


def _complete(session: Session, key: ApiKey, *items: EmbeddingCompleteItem) -> list[EmbeddingItemResult]:
    return EmbeddingCompletion(session, clock=lambda: NOW).complete(key.id, list(items))


def _item(task: EmbeddingTask, session: Session, **overrides: object) -> EmbeddingCompleteItem:
    fields: dict[str, object] = {
        "task_id": task.id,
        "text_hash": current_hash(session, task),
        "model": MODEL,
        "vector": unit_vector(0),
    }
    return EmbeddingCompleteItem.model_validate({**fields, **overrides})


def _embeddings(session: Session) -> list[CandidateEmbedding]:
    return list(session.scalars(select(CandidateEmbedding)))


def test_complete_stores_the_vector_and_completes_the_task(db_session: Session) -> None:
    candidate, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    (result,) = _complete(db_session, key, _item(task, db_session))

    assert (result.task_id, result.outcome, result.reason) == (task.id, EmbeddingOutcome.STORED, None)
    (stored,) = _embeddings(db_session)
    assert (stored.candidate_id, stored.model, stored.locale, stored.dim) == (candidate.id, MODEL, "de", EMBEDDING_DIM)
    assert stored.text_hash == current_hash(db_session, task)
    assert (task.status, task.lease_expires_at) == (WorkTaskStatus.COMPLETED, None)


def test_a_stored_vector_is_found_by_cosine_distance(db_session: Session) -> None:
    (near, near_task), (far, far_task) = queued(db_session, "Nah"), queued(db_session, "Fern")
    key = make_key(db_session)
    for task in (near_task, far_task):
        claimed_by(db_session, task, key)
    _complete(
        db_session,
        key,
        _item(near_task, db_session, vector=unit_vector(0)),
        _item(far_task, db_session, vector=unit_vector(1)),
    )

    ranked = db_session.scalars(
        select(CandidateEmbedding.candidate_id).order_by(CandidateEmbedding.embedding.cosine_distance(unit_vector(0)))
    ).all()

    assert list(ranked) == [near.id, far.id]


def test_a_later_text_replaces_the_stored_vector_of_the_same_target(db_session: Session) -> None:
    candidate, first = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, first, key)
    _complete(db_session, key, _item(first, db_session, vector=unit_vector(0)))
    row = db_session.get(CandidateSearchText, (candidate.id, "de"))
    assert row is not None
    row.content_hash = "second"
    EmbeddingEnqueuer(db_session, MODEL).enqueue(candidate.id, BuiltText("de", row.text, "second"))
    (second,) = [t for t in db_session.scalars(select(EmbeddingTask)) if t.status is WorkTaskStatus.PENDING]
    claimed_by(db_session, second, key)

    _complete(db_session, key, _item(second, db_session, vector=unit_vector(2)))

    (stored,) = _embeddings(db_session)
    assert (stored.text_hash, stored.embedding[2]) == ("second", 1.0)


def test_a_stale_hash_is_discarded_and_a_fresh_task_is_queued(db_session: Session) -> None:
    candidate, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    old_hash = current_hash(db_session, task)
    db_session.get(CandidateSearchText, (candidate.id, "de")).content_hash = "newer"  # type: ignore[union-attr]
    db_session.flush()

    (result,) = _complete(db_session, key, _item(task, db_session, text_hash=old_hash))

    assert result.outcome is EmbeddingOutcome.STALE
    assert _embeddings(db_session) == []
    assert task.status is WorkTaskStatus.COMPLETED
    (fresh,) = [t for t in db_session.scalars(select(EmbeddingTask)) if t.status is WorkTaskStatus.PENDING]
    assert (fresh.candidate_id, fresh.text_hash) == (candidate.id, "newer")


def test_a_hash_that_is_not_the_one_the_task_was_leased_for_is_stale_even_when_it_is_current(
    db_session: Session,
) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    current = current_hash(db_session, task)
    task.text_hash = "leased-for-something-else"
    db_session.flush()

    (result,) = _complete(db_session, key, _item(task, db_session, text_hash=current))

    assert result.outcome is EmbeddingOutcome.STALE
    assert _embeddings(db_session) == []


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"model": "some-other-model"}, "model"),
        ({"vector": [0.0] * (EMBEDDING_DIM - 1)}, "dimension"),
        ({"vector": [0.0] * (EMBEDDING_DIM + 1)}, "dimension"),
        ({"vector": [float("nan")] + [0.0] * (EMBEDDING_DIM - 1)}, "finite"),
        ({"vector": [float("inf")] + [0.0] * (EMBEDDING_DIM - 1)}, "finite"),
    ],
)
def test_a_wrong_model_dimension_or_non_finite_value_is_rejected_and_the_task_failed(
    db_session: Session, override: dict[str, object], reason: str
) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)

    (result,) = _complete(db_session, key, _item(task, db_session, **override))

    assert result.outcome is EmbeddingOutcome.REJECTED
    assert result.reason is not None and reason in result.reason
    assert _embeddings(db_session) == []
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, result.reason)


def test_one_bad_item_never_fails_the_batch(db_session: Session) -> None:
    (good_a, task_a), (_, bad), (good_c, task_c) = (queued(db_session, f"Antrag {n}") for n in range(3))
    key = make_key(db_session)
    for task in (task_a, bad, task_c):
        claimed_by(db_session, task, key)

    results = _complete(
        db_session,
        key,
        _item(task_a, db_session),
        _item(bad, db_session, vector=[1.0]),
        _item(task_c, db_session, vector=unit_vector(3)),
    )

    assert [result.outcome for result in results] == [
        EmbeddingOutcome.STORED,
        EmbeddingOutcome.REJECTED,
        EmbeddingOutcome.STORED,
    ]
    assert {row.candidate_id for row in _embeddings(db_session)} == {good_a.id, good_c.id}


def test_a_task_claimed_by_another_key_is_rejected_and_left_alone(db_session: Session) -> None:
    _, task = queued(db_session)
    owner, intruder = make_key(db_session, "owner"), make_key(db_session, "intruder")
    claimed_by(db_session, task, owner)

    (result,) = _complete(db_session, intruder, _item(task, db_session))

    assert result.outcome is EmbeddingOutcome.REJECTED
    assert _embeddings(db_session) == []
    assert (task.status, task.claimed_by_api_key_id) == (WorkTaskStatus.CLAIMED, owner.id)


def test_an_unknown_task_and_a_task_that_is_not_claimed_are_rejected(db_session: Session) -> None:
    _, pending = queued(db_session)
    key = make_key(db_session)

    unknown = EmbeddingCompleteItem(task_id=uuid.uuid4(), text_hash="h", model=MODEL, vector=unit_vector())
    results = _complete(db_session, key, unknown, _item(pending, db_session))

    assert [result.outcome for result in results] == [EmbeddingOutcome.REJECTED, EmbeddingOutcome.REJECTED]
    assert pending.status is WorkTaskStatus.PENDING


def test_completing_the_same_task_twice_stores_once_and_rejects_the_repeat(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    item = _item(task, db_session)

    results = _complete(db_session, key, item, item)

    assert [result.outcome for result in results] == [EmbeddingOutcome.STORED, EmbeddingOutcome.REJECTED]
    assert len(_embeddings(db_session)) == 1


def test_an_expired_but_unreclaimed_lease_still_completes_with_a_current_hash(db_session: Session) -> None:
    _, task = queued(db_session)
    key = make_key(db_session)
    claimed_by(db_session, task, key)
    task.lease_expires_at = NOW - timedelta(minutes=1)
    db_session.flush()

    (result,) = _complete(db_session, key, _item(task, db_session))

    assert result.outcome is EmbeddingOutcome.STORED


def test_the_check_of_the_current_text_blocks_a_concurrent_rewrite_until_the_batch_settles(
    db_session: Session,
) -> None:
    """The row lock is what stops a text change slipping between the hash check and the stored vector."""
    with (
        committed_world(tasks=1) as (world, (key, _)),
        Session(bind=db_engine) as completing,
        Session(bind=db_engine) as rewriting,
    ):
        task = completing.get(EmbeddingTask, world.task_ids[0])
        assert task is not None
        claimed_by(completing, task, key)
        _complete(completing, key, _item(task, completing))
        rewriting.execute(text("SET LOCAL lock_timeout = '300ms'"))

        with pytest.raises(OperationalError):
            rewriting.execute(
                text("UPDATE candidate_search_text SET content_hash = 'x' WHERE candidate_id = :id"),
                {"id": world.candidate_ids[0]},
            )
        rewriting.rollback()
        completing.rollback()


def test_a_worker_whose_lease_was_reclaimed_by_another_key_cannot_complete_the_task(db_session: Session) -> None:
    _, task = queued(db_session)
    slow, fast = make_key(db_session, "slow"), make_key(db_session, "fast")
    claimed_by(db_session, task, slow)
    later = EmbeddingQueue(db_session, clock=lambda: NOW + timedelta(minutes=16))
    (served,) = later.claim(fast.id, MODEL, limit=1).items

    (late,) = _complete(db_session, slow, _item(task, db_session))
    (timely,) = _complete(db_session, fast, _item(task, db_session))

    assert (served.task_id, late.outcome, timely.outcome) == (
        task.id,
        EmbeddingOutcome.REJECTED,
        EmbeddingOutcome.STORED,
    )
    assert len(_embeddings(db_session)) == 1
