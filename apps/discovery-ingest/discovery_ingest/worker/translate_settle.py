"""Settle the tasks of a translate batch: post the valid text, fail the rest, record each outcome, track what is open."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.translation.errors import TransientError, TranslationEngineError, UnusableOutputError
from discovery_ingest.translation.repair import Checked
from discovery_ingest.translation_models import (
    ClaimedTranslationTask,
    TranslationCompleteItem,
    TranslationItemResult,
    TranslationOutcome,
)
from discovery_ingest.worker.lease_settle import Failure, fail_batch
from discovery_ingest.worker.open_tasks import OpenTasks
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import COMPLETED, REJECTED, STALE, UNAVAILABLE, Tally

_LABELS: Mapping[TranslationOutcome, str] = {
    "stored": COMPLETED,
    "stale": STALE,
    "rejected": REJECTED,
    "unavailable": UNAVAILABLE,
}
INVALID_PREFIX = "validation failed after one repair: "


def failure_of(err: TranslationEngineError) -> Failure:
    """Return how to fail the tasks of a batch the engine could not translate: a retry helps only for a transient error or a bad answer."""
    return Failure(str(err), retryable=isinstance(err, TransientError | UnusableOutputError))


def record_results(results: Sequence[TranslationItemResult], tally: Tally) -> None:
    """Count one outcome per posted translation; a rejection (including a replayed complete) is logged, never fatal."""
    for result in results:
        tally.record(_LABELS[result.outcome])
        if result.outcome == "rejected":
            print(f"translation task {result.task_id} rejected: {result.reason}", file=sys.stderr)


def _stop_if_unavailable(results: Sequence[TranslationItemResult]) -> None:
    unavailable = [result for result in results if result.outcome == "unavailable"]
    if unavailable:
        raise StopDrain("storage_unavailable", unavailable[0].reason or "the object store is unavailable")


def _item(task: ClaimedTranslationTask, checked: Checked, engine: str) -> TranslationCompleteItem:
    translated = checked.translated
    return TranslationCompleteItem(
        task_id=task.task_id,
        source_hash=task.source_hash,
        title=translated.title,
        description=translated.description,
        engine=engine,
        model=checked.model,
    )


@dataclass(frozen=True, slots=True)
class BatchState:
    """What the settlement of one batch shares: the client, the engine name, the open tasks and the tally."""

    client: DiscoveryIngestClient
    engine: str
    open_tasks: OpenTasks[ClaimedTranslationTask]
    tally: Tally


class GroupSettler:
    """Settle the tasks of one locale group; its units are keyed by task id."""

    def __init__(self, state: BatchState, group: Sequence[ClaimedTranslationTask]) -> None:
        """Index the ``group`` by the key its units carry."""
        self._state = state
        self._group = list(group)
        self._by_key = {str(task.task_id): task for task in group}

    def post(self, valid: Sequence[Checked]) -> None:
        """Post the translations of ``valid`` units and record what the API answered.

        Raises :class:`StopDrain` (``storage_unavailable``) when the API could not store an item: it has handed that
        task back, so the drain ends instead of retrying in a loop.
        """
        if not valid:
            return
        state = self._state
        items = [_item(self._by_key[checked.source.key], checked, state.engine) for checked in valid]
        results = state.client.translations.complete(items).items
        state.open_tasks.settled(result.task_id for result in results)
        record_results(results, state.tally)
        _stop_if_unavailable(results)

    def fail_invalid(self, invalid: Sequence[Checked]) -> None:
        """Fail each unit that is still invalid after its repair, for good and with its reasons."""
        for checked in invalid:
            failure = Failure(INVALID_PREFIX + "; ".join(checked.problems()), retryable=False)
            self._fail([self._by_key[checked.source.key]], failure)
            self._state.tally.invalid += 1

    def fail_unfinished(self, failure: Failure) -> None:
        """Fail the tasks of the group that no result has settled, because the engine could not translate them."""
        self._fail(self._state.open_tasks.among(self._group), failure)

    def _fail(self, tasks: Sequence[ClaimedTranslationTask], failure: Failure) -> None:
        state = self._state
        for label in fail_batch(state.client.translations, tasks, failure):
            state.tally.record(label)
        state.open_tasks.settled(task.task_id for task in tasks)
