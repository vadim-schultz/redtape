"""Hash-aware, idempotent enqueue of translation tasks, one per target locale that lacks a current translation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.translation.plan import Classification, EnqueueTotals, Slot, slots_for
from app.features.translation.priority import first_priority, retranslation_priority
from app.features.translation.repository import TranslationRepository
from app.features.translation.snapshot_enqueue import SnapshotEnqueuer
from app.features.translation.source import SourceRepository
from app.features.translation.task_repository import TaskRepository

UPGRADE_SWEEP_LIMIT: Final = 200
"""Most tail rows one upgrade sweep queues; a sweep is bounded like a backfill, and the next run takes the rest."""


class TranslationEnqueuer:
    """Queue the translations a candidate's card unit needs; a repeat with nothing changed writes nothing."""

    def __init__(self, session: Session, locales: Sequence[str] | None = None) -> None:
        """Bind the enqueuer to ``session`` and the target ``locales`` (the configured ones by default)."""
        self._locales = tuple(settings.translation_target_locale_codes if locales is None else locales)
        self._source = SourceRepository(session)
        self._index = TranslationRepository(session)
        self._tasks = TaskRepository(session)
        self._snapshots = SnapshotEnqueuer(session, self._locales)

    def enqueue_many(self, candidate_ids: Sequence[UUID], pages: Sequence[UUID] = ()) -> EnqueueTotals:
        """Queue every missing or stale translation of ``candidate_ids`` and report what each slot needed.

        ``pages`` are the procedure pages the same mentions cite; each one queues its snapshot translations (see
        :class:`SnapshotEnqueuer`). A pending task takes the new hash and priority; a claimed task is left alone, because
        its result will be discarded as stale and the task re-queued when it is settled. A human translation is never
        queued over.
        """
        self._snapshots.enqueue_pages(pages)
        if not self._locales:
            return EnqueueTotals()
        units = self._source.units_for(candidate_ids)
        rows = self._index.index_states(candidate_ids, self._locales)
        slots = slots_for(candidate_ids, self._locales, units, rows)
        self._tasks.retire_pending([slot.key for slot in slots if slot.kind in _SETTLED])
        totals = EnqueueTotals(counts=Counter(slot.kind for slot in slots))
        totals.enqueued = self._queue([slot for slot in slots if slot.kind in _NEEDS_WORK])
        return totals

    def enqueue_upgrades(self, now: datetime, limit: int = UPGRADE_SWEEP_LIMIT) -> int:
        """Queue an Azure upgrade for up to ``limit`` tail rows of the target locales; return how many were queued.

        A tail row is a machine translation the tail engine wrote. Nothing is queued while an Azure task is ready, so
        upgrades run on idle Azure capacity. A human row is never queued, and an open task keeps its priority.
        """
        return self._tasks.queue_upgrades(self._locales, now, limit)

    def _queue(self, work: Sequence[Slot]) -> int:
        confidences = self._source.confidences_for(list(dict.fromkeys(slot.candidate_id for slot in work)))
        return sum(self._upsert(slot, confidences[slot.candidate_id]) for slot in work)

    def _upsert(self, slot: Slot, confidence: float) -> bool:
        assert slot.source_hash is not None
        priority = _PRIORITY[slot.kind](confidence)
        return self._tasks.upsert_pending(slot.candidate_id, slot.locale, slot.source_hash, priority)


_NEEDS_WORK = frozenset({Classification.MISSING, Classification.STALE})
_SETTLED = frozenset({Classification.CURRENT, Classification.HUMAN})
_PRIORITY: Mapping[Classification, Callable[[float], int]] = {
    Classification.MISSING: first_priority,
    Classification.STALE: retranslation_priority,
}
