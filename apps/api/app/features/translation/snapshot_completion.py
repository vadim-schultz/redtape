"""Completing snapshot tasks: ownership, the ordered checks, then the outcome's write, and the refusals that settle a task."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import utc_now
from app.features.search.leased_queue import LeasedQueue
from app.features.search.task_settle import complete_task, fail_task
from app.features.translation.snapshot_checks import Facts, Refusal, Settlement, first_refusal
from app.features.translation.snapshot_outcomes import SnapshotOutcomes, result
from app.features.translation.snapshot_repository import SnapshotRepository, page_key
from app.features.translation.task_repository import TaskRepository
from app.models.snapshot_translation import SnapshotTranslationTask
from app.schema.translation.snapshot_machine import (
    SnapshotAnswer,
    SnapshotCompleteItem,
    SnapshotItemOutcome,
    SnapshotItemResult,
)
from app.shared.object_store import ObjectStore

NOT_OWNED: Final = "task is not claimed by this key"


class SnapshotCompletion:
    """Settle the page results a worker posts: write the current ones, requeue stale ones and refuse invalid ones."""

    def __init__(self, session: Session, store: ObjectStore | None, artifacts: ArtifactReadService) -> None:
        """Bind the completion to ``session``, the object ``store`` (``None`` when not configured) and the artifact reads."""
        self._session = session
        self._leased = LeasedQueue(session, SnapshotTranslationTask)
        self._index = SnapshotRepository(session)
        self._tasks = TaskRepository(session)
        self._artifacts = artifacts
        self._outcomes = SnapshotOutcomes(session, store)
        self._handlers: dict[SnapshotItemOutcome, Callable[[Facts], SnapshotItemResult]] = {
            SnapshotItemOutcome.TRANSLATED: self._outcomes.translated,
            SnapshotItemOutcome.UNCHANGED: self._outcomes.unchanged,
            SnapshotItemOutcome.SKIPPED: self._outcomes.skipped,
        }

    def complete(self, api_key_id: UUID, items: Sequence[SnapshotCompleteItem]) -> list[SnapshotItemResult]:
        """Return one result per item, in order; one item that is stale or invalid never affects the others."""
        results = [self._complete_one(api_key_id, item) for item in items]
        self._session.flush()
        return results

    def _complete_one(self, api_key_id: UUID, item: SnapshotCompleteItem) -> SnapshotItemResult:
        task = self._leased.owned(item.task_id, api_key_id)
        if task is None:
            return result(item.task_id, SnapshotAnswer.REJECTED, NOT_OWNED)
        facts = self._facts(task, item)
        refusal = first_refusal(facts)
        return self._refuse(facts, refusal) if refusal else self._handlers[item.outcome](facts)

    def _facts(self, task: SnapshotTranslationTask, item: SnapshotCompleteItem) -> Facts:
        latest = self._artifacts.latest_snapshot(task.catalogue_service_id)
        return Facts(task, item, latest, self._index.locked_row(page_key(task)))

    def _refuse(self, facts: Facts, refusal: Refusal) -> SnapshotItemResult:
        settle = {Settlement.FAIL: self._settle_failed, Settlement.REQUEUE: self._settle_requeued}[refusal.settlement]
        settle(facts, refusal)
        return result(facts.task.id, refusal.outcome, refusal.reason)

    def _settle_failed(self, facts: Facts, refusal: Refusal) -> None:
        fail_task(facts.task, refusal.reason, FailureKind.PERMANENT, utc_now())

    def _settle_requeued(self, facts: Facts, _: Refusal) -> None:
        """Complete the stale task and queue the page again against the artifact that is now the latest."""
        complete_task(facts.task)
        self._session.flush()
        assert facts.latest is not None
        self._tasks.upsert_snapshot_pending(page_key(facts.task), facts.latest.sha256, facts.task.priority)
