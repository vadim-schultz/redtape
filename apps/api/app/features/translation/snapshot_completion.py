"""Completing snapshot tasks: ownership, the ordered checks, then the object write or the skip marker, and the index row."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import utc_now
from app.features.search.leased_queue import LeasedQueue
from app.features.search.task_settle import complete_task, fail_task, release_task
from app.features.translation.deferred import AfterCommitDeletes
from app.features.translation.snapshot_checks import Facts, Refusal, Settlement, first_refusal
from app.features.translation.snapshot_repository import PageKey, SnapshotRepository, SnapshotRowValues
from app.features.translation.snapshot_store import SnapshotPayload, SnapshotStore
from app.features.translation.store import StoredObject
from app.features.translation.task_repository import TaskRepository
from app.models.snapshot_translation import SnapshotTranslationTask
from app.schema.translation.snapshot_machine import (
    SnapshotAnswer,
    SnapshotCompleteItem,
    SnapshotItemOutcome,
    SnapshotItemResult,
)
from app.shared.object_store import ObjectStore, ObjectStoreUnavailableError

NOT_OWNED: Final = "task is not claimed by this key"
SKIPPED_ENGINE: Final = "none"
"""The engine column of a skip marker: no engine ran, because the page was not translated."""


def _result(task_id: UUID, answer: SnapshotAnswer, reason: str | None = None) -> SnapshotItemResult:
    return SnapshotItemResult(task_id=task_id, outcome=answer, reason=reason)


def _key(task: SnapshotTranslationTask) -> PageKey:
    return task.catalogue_service_id, task.locale


def _payload(facts: Facts) -> SnapshotPayload:
    """Return the object body of a translated item: its blocks, its provenance and the page's source URL."""
    item, latest = facts.item, facts.latest
    assert item.blocks is not None and item.engine is not None and latest is not None
    return SnapshotPayload(
        locale=facts.task.locale,
        source_hash=item.source_hash,
        engine=item.engine,
        model=item.model,
        truncated=item.truncated,
        source_url=latest.source_url,
        blocks=item.blocks,
    )


class SnapshotCompletion:
    """Settle the page results a worker posts: store the current ones, discard stale ones and refuse invalid ones."""

    def __init__(self, session: Session, store: ObjectStore | None, artifacts: ArtifactReadService) -> None:
        """Bind the completion to ``session``, the object ``store`` (``None`` when not configured) and the artifact reads."""
        self._session = session
        self._store = store
        self._leased = LeasedQueue(session, SnapshotTranslationTask)
        self._index = SnapshotRepository(session)
        self._tasks = TaskRepository(session)
        self._artifacts = artifacts
        self._replaced = AfterCommitDeletes(session, store)
        self._handlers: dict[SnapshotItemOutcome, Callable[[Facts], SnapshotItemResult]] = {
            SnapshotItemOutcome.TRANSLATED: self._store_translated,
            SnapshotItemOutcome.UNCHANGED: self._keep_unchanged,
            SnapshotItemOutcome.SKIPPED: self._mark_skipped,
        }

    def complete(self, api_key_id: UUID, items: Sequence[SnapshotCompleteItem]) -> list[SnapshotItemResult]:
        """Return one result per item, in order; one item that is stale or invalid never affects the others."""
        results = [self._complete_one(api_key_id, item) for item in items]
        self._session.flush()
        return results

    def _complete_one(self, api_key_id: UUID, item: SnapshotCompleteItem) -> SnapshotItemResult:
        task = self._leased.owned(item.task_id, api_key_id)
        if task is None:
            return _result(item.task_id, SnapshotAnswer.REJECTED, NOT_OWNED)
        facts = self._facts(task, item)
        refusal = first_refusal(facts)
        return self._refuse(facts, refusal) if refusal else self._handlers[item.outcome](facts)

    def _facts(self, task: SnapshotTranslationTask, item: SnapshotCompleteItem) -> Facts:
        latest = self._artifacts.latest_snapshot(task.catalogue_service_id)
        return Facts(task, item, latest, self._index.locked_row(_key(task)))

    def _refuse(self, facts: Facts, refusal: Refusal) -> SnapshotItemResult:
        settle = {Settlement.FAIL: self._settle_failed, Settlement.REQUEUE: self._settle_requeued}[refusal.settlement]
        settle(facts, refusal)
        return _result(facts.task.id, refusal.outcome, refusal.reason)

    def _settle_failed(self, facts: Facts, refusal: Refusal) -> None:
        fail_task(facts.task, refusal.reason, FailureKind.PERMANENT, utc_now())

    def _settle_requeued(self, facts: Facts, _: Refusal) -> None:
        """Complete the stale task and queue the page again against the artifact that is now the latest."""
        complete_task(facts.task)
        self._session.flush()
        assert facts.latest is not None
        self._tasks.upsert_snapshot_pending(_key(facts.task), facts.latest.sha256, facts.task.priority)

    def _store_translated(self, facts: Facts) -> SnapshotItemResult:
        payload = _payload(facts)
        try:
            stored = SnapshotStore(self._store).write(facts.task.catalogue_service_id, payload)
        except ObjectStoreUnavailableError as err:
            release_task(facts.task, str(err))
            return _result(facts.task.id, SnapshotAnswer.UNAVAILABLE, str(err))
        self._store_row(facts, _row(facts, payload, stored))
        self._retire_previous(facts, keep=stored.key)
        return _result(facts.task.id, SnapshotAnswer.STORED)

    def _keep_unchanged(self, facts: Facts) -> SnapshotItemResult:
        self._index.refresh_artifact(_key(facts.task), facts.item.artifact_sha256)
        complete_task(facts.task)
        return _result(facts.task.id, SnapshotAnswer.UNCHANGED)

    def _mark_skipped(self, facts: Facts) -> SnapshotItemResult:
        item = facts.item
        assert item.skipped_reason is not None
        values = SnapshotRowValues(
            artifact_sha256=item.artifact_sha256,
            source_hash=item.source_hash,
            engine=SKIPPED_ENGINE,
            model=None,
            storage_key=None,
            content_sha256=None,
            size_bytes=None,
            truncated=False,
            skipped_reason=item.skipped_reason.value,
        )
        self._store_row(facts, values)
        self._retire_previous(facts, keep=None)
        return _result(facts.task.id, SnapshotAnswer.SKIPPED)

    def _store_row(self, facts: Facts, values: SnapshotRowValues) -> None:
        self._index.upsert_row(_key(facts.task), values)
        complete_task(facts.task)

    def _retire_previous(self, facts: Facts, keep: str | None) -> None:
        """Delete after commit the object the row pointed at before, unless it is the object just written."""
        previous = facts.existing.storage_key if facts.existing is not None else None
        if previous is not None and previous != keep:
            self._replaced.add(previous)


def _row(facts: Facts, payload: SnapshotPayload, stored: StoredObject) -> SnapshotRowValues:
    """Return the index row of a translated page: the object it points at and the provenance of its text."""
    return SnapshotRowValues(
        artifact_sha256=facts.item.artifact_sha256,
        source_hash=payload.source_hash,
        engine=payload.engine,
        model=payload.model,
        storage_key=stored.key,
        content_sha256=stored.content_sha256,
        size_bytes=stored.size_bytes,
        truncated=payload.truncated,
        skipped_reason=None,
    )
