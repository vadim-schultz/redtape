"""Completing translation tasks: ownership, the ordered checks, then the object write and the index row."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import Clock, utc_now
from app.features.search.leased_queue import LeasedQueue
from app.features.search.task_settle import complete_task, fail_task, release_task
from app.features.translation.checks import Facts, Refusal, Settlement, first_refusal
from app.features.translation.deferred import AfterCommitDeletes
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.events import StoredSubscriber, TranslationStoredEvents
from app.features.translation.repository import TranslationRepository
from app.features.translation.source import SourceRepository
from app.features.translation.store import StoredObject, TranslationPayload, TranslationStore
from app.features.translation.text import clean
from app.models.translation import TranslationSource, TranslationTask
from app.schema.translation.machine import TranslationCompleteItem, TranslationItemResult, TranslationOutcome
from app.shared.object_store import ObjectStore, ObjectStoreUnavailableError

NOT_OWNED = "task is not claimed by this key"


def _result(task_id: UUID, outcome: TranslationOutcome, reason: str | None = None) -> TranslationItemResult:
    return TranslationItemResult(task_id=task_id, outcome=outcome, reason=reason)


class TranslationCompletion:
    """Settle the translations a worker posts: store the current ones, discard stale ones and refuse invalid ones."""

    def __init__(
        self,
        session: Session,
        store: ObjectStore | None,
        clock: Clock = utc_now,
        subscribers: Sequence[StoredSubscriber] = (),
    ) -> None:
        """Bind the completion to ``session`` and the object ``store`` (``None`` when not configured)."""
        self._session = session
        self._store = store
        self._clock = clock
        self._leased = LeasedQueue(session, TranslationTask)
        self._index = TranslationRepository(session)
        self._source = SourceRepository(session)
        self._events = TranslationStoredEvents(session, subscribers)
        self._replaced = AfterCommitDeletes(session, store)

    def complete(self, api_key_id: UUID, items: Sequence[TranslationCompleteItem]) -> list[TranslationItemResult]:
        """Return one result per item, in order; one item that is stale or invalid never affects the others."""
        results = [self._complete_one(api_key_id, item) for item in items]
        self._session.flush()
        return results

    def _complete_one(self, api_key_id: UUID, item: TranslationCompleteItem) -> TranslationItemResult:
        self._index.share_lock_candidate_of(item.task_id)
        task = self._leased.owned(item.task_id, api_key_id)
        if task is None:
            return _result(item.task_id, TranslationOutcome.REJECTED, NOT_OWNED)
        facts = self._facts(task, item)
        refusal = first_refusal(facts)
        return self._refuse(task, refusal) if refusal else self._store_text(facts)

    def _facts(self, task: TranslationTask, item: TranslationCompleteItem) -> Facts:
        unit = self._source.units_for([task.candidate_id]).get(task.candidate_id)
        existing = self._index.locked_row(task.candidate_id, task.locale)
        return Facts(task, item, unit.source_hash if unit else None, existing)

    def _refuse(self, task: TranslationTask, refusal: Refusal) -> TranslationItemResult:
        settle = {
            Settlement.FAIL: self._settle_failed,
            Settlement.COMPLETE: self._settle_completed,
            Settlement.REQUEUE: self._settle_requeued,
        }[refusal.settlement]
        settle(task, refusal)
        return _result(task.id, refusal.outcome, refusal.reason)

    def _settle_failed(self, task: TranslationTask, refusal: Refusal) -> None:
        fail_task(task, refusal.reason, FailureKind.PERMANENT, self._clock())

    def _settle_completed(self, task: TranslationTask, _: Refusal) -> None:
        complete_task(task)

    def _settle_requeued(self, task: TranslationTask, refusal: Refusal) -> None:
        self._settle_completed(task, refusal)
        self._requeue(task)

    def _requeue(self, task: TranslationTask) -> None:
        self._session.flush()
        TranslationEnqueuer(self._session, [task.locale]).enqueue_many([task.candidate_id])

    def _store_text(self, facts: Facts) -> TranslationItemResult:
        task, payload = facts.task, self._payload(facts)
        try:
            stored = TranslationStore(self._store).write(task.candidate_id, payload)
        except ObjectStoreUnavailableError as err:
            return self._hand_back(task, err)
        self._move_index_row(facts, payload, stored)
        return _result(task.id, TranslationOutcome.STORED)

    def _hand_back(self, task: TranslationTask, err: ObjectStoreUnavailableError) -> TranslationItemResult:
        """Return the task to the queue without consuming an attempt: the store, not the text, stopped the work."""
        release_task(task, str(err))
        return _result(task.id, TranslationOutcome.UNAVAILABLE, str(err))

    def _move_index_row(self, facts: Facts, payload: TranslationPayload, stored: StoredObject) -> None:
        task, replaced_key = facts.task, facts.existing.storage_key if facts.existing else None
        self._index.upsert_row(task.candidate_id, payload, stored, facts.existing)
        complete_task(task)
        self._events.publish(task.candidate_id, task.locale, payload)
        if replaced_key is not None and replaced_key != stored.key:
            self._replaced.add(replaced_key)

    def _payload(self, facts: Facts) -> TranslationPayload:
        text = clean(facts.item)
        return TranslationPayload(
            locale=facts.task.locale,
            title=text.title,
            description=text.description,
            source_hash=facts.item.source_hash,
            source=TranslationSource.MT,
            engine=facts.item.engine,
            model=facts.item.model,
        )
