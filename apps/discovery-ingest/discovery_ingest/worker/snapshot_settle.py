"""Settle a claimed page: post, validate, record, and fail or release the task.

Every settle call marks its task settled in the batch's open tasks, so a stop releases only what nobody settled.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import (
    ClaimedSnapshotTask,
    SnapshotCompleteItem,
    SnapshotItemResult,
    SnapshotRowBlock,
    SnapshotTextBlock,
    SnapshotWireBlock,
)
from discovery_ingest.snapshot_translation import (
    Block,
    Rejected,
    SkippedPage,
    SourcePage,
    TranslatedPage,
    finish_page,
)
from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.repair import Translator
from discovery_ingest.worker.lease_settle import Failure, fail_batch, release_batch
from discovery_ingest.worker.open_tasks import OpenTasks
from discovery_ingest.worker.snapshot_translate import translate_page, translated_blocks
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import COMPLETED, REJECTED, SKIPPED, STALE, UNAVAILABLE, UNCHANGED, Tally
from discovery_ingest.worker.translate_settle import failure_of

_LABELS = {
    "stored": COMPLETED,
    "unchanged": UNCHANGED,
    "skipped": SKIPPED,
    "stale": STALE,
    "rejected": REJECTED,
    "unavailable": UNAVAILABLE,
}


def wire_blocks(blocks: Sequence[Block]) -> list[SnapshotWireBlock]:
    """Return ``blocks`` in the API's shape: a row carries its cells, every other kind its text."""
    return [SnapshotRowBlock(kind="row", cells=list(b.texts)) if b.kind == "row" else _text(b) for b in blocks]


def _text(block: Block) -> SnapshotTextBlock:
    return SnapshotTextBlock(kind=block.kind, text=block.texts[0])


def _record(results: Sequence[SnapshotItemResult], tally: Tally) -> None:
    for result in results:
        tally.record(_LABELS[result.outcome])
        if result.outcome == "rejected":
            print(f"snapshot task {result.task_id} rejected: {result.reason}", file=sys.stderr)


def _stop_if_unavailable(results: Sequence[SnapshotItemResult]) -> None:
    for result in results:
        if result.outcome == "unavailable":
            raise StopDrain("storage_unavailable", result.reason or "the object store is unavailable")


@dataclass(frozen=True, slots=True)
class PageSettler:
    """Settle the pages of one batch: the client, the metered translator, the engine's name, the tally and the open tasks."""

    client: DiscoveryIngestClient
    translator: Translator
    engine: str
    tally: Tally
    open_tasks: OpenTasks[ClaimedSnapshotTask]

    def skipped(self, task: ClaimedSnapshotTask, page: SkippedPage) -> None:
        """Post the skip marker of a page the pipeline does not translate; no engine call and no characters."""
        item = SnapshotCompleteItem(
            task_id=task.task_id,
            artifact_sha256=task.artifact_sha256,
            source_hash=page.source_hash,
            outcome="skipped",
            skipped_reason=page.reason.value,
        )
        self._post(task, item)

    def unchanged(self, task: ClaimedSnapshotTask, page: SourcePage) -> None:
        """Post the cleaned text's hash for a page whose text is already stored: the API keeps the object as it is."""
        item = SnapshotCompleteItem(
            task_id=task.task_id,
            artifact_sha256=task.artifact_sha256,
            source_hash=page.source_hash,
            outcome="unchanged",
        )
        self._post(task, item)

    def translated(self, task: ClaimedSnapshotTask, page: SourcePage) -> None:
        """Translate the page, validate it, then post it; a refused page fails the task, an engine error fails it as the error says."""
        try:
            outcome = translate_page(self.translator, task.locale, page)
        except TranslationEngineError as err:
            self.fail(task, failure_of(err))
            return
        self.tally.llm_calls += 1
        checked = finish_page(page, translated_blocks(page, outcome))
        if isinstance(checked, Rejected):
            self._refuse(task, checked)
            return
        self.tally.untranslated_blocks += checked.untranslated
        self._post(task, self._translated_item(task, checked, outcome.model))

    def fail(self, task: ClaimedSnapshotTask, failure: Failure) -> None:
        """Fail one claimed page with ``failure``; the task is settled whatever the API answers."""
        for label in fail_batch(self.client.snapshots, [task], failure):
            self.tally.record(label)
        self.open_tasks.settled([task.task_id])

    def release(self, task: ClaimedSnapshotTask, reason: str) -> None:
        """Hand one claimed page back without consuming an attempt; the task is settled whatever the API answers."""
        self.tally.released += release_batch(self.client.snapshots, [task], reason)
        self.open_tasks.settled([task.task_id])

    def _refuse(self, task: ClaimedSnapshotTask, rejected: Rejected) -> None:
        self.tally.invalid += 1
        self.fail(task, Failure(rejected.reason, retryable=False))

    def _translated_item(
        self, task: ClaimedSnapshotTask, checked: TranslatedPage, model: str | None
    ) -> SnapshotCompleteItem:
        return SnapshotCompleteItem(
            task_id=task.task_id,
            artifact_sha256=task.artifact_sha256,
            source_hash=checked.source_hash,
            outcome="translated",
            blocks=wire_blocks(checked.blocks),
            truncated=checked.truncated,
            engine=self.engine,
            model=model,
        )

    def _post(self, task: ClaimedSnapshotTask, item: SnapshotCompleteItem) -> None:
        results = self.client.snapshots.complete([item]).items
        self.open_tasks.settled([task.task_id])
        _record(results, self.tally)
        _stop_if_unavailable(results)
