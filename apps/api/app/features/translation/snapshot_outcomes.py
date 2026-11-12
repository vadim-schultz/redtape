"""The three writes a valid page result makes: translated blocks into the object store, an unchanged hash, or a skip marker."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.features.search.task_settle import complete_task, release_task
from app.features.translation.deferred import AfterCommitDeletes
from app.features.translation.snapshot_checks import Facts
from app.features.translation.snapshot_repository import SnapshotRepository, SnapshotRowValues, page_key
from app.features.translation.snapshot_store import SnapshotPayload, SnapshotStore
from app.features.translation.store import StoredObject
from app.schema.translation.snapshot_machine import SnapshotAnswer, SnapshotItemResult
from app.shared.object_store import ObjectStore, ObjectStoreUnavailableError


def result(task_id: UUID, answer: SnapshotAnswer, reason: str | None = None) -> SnapshotItemResult:
    """Return the answer to one posted item, with the reason a refusal or an unavailable store carries."""
    return SnapshotItemResult(task_id=task_id, outcome=answer, reason=reason)


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


class SnapshotOutcomes:
    """Write what a valid page result means: a stored object, a moved artifact hash, or a skip marker."""

    def __init__(self, session: Session, store: ObjectStore | None) -> None:
        """Bind the writes to ``session`` and the object ``store``; objects they replace are deleted after commit."""
        self._store = store
        self._index = SnapshotRepository(session)
        self._replaced = AfterCommitDeletes(session, store)

    def translated(self, facts: Facts) -> SnapshotItemResult:
        """Write the blocks as an object and point the index row at it; without a store the task is released."""
        payload = _payload(facts)
        try:
            stored = SnapshotStore(self._store).write(facts.task.catalogue_service_id, payload)
        except ObjectStoreUnavailableError as err:
            release_task(facts.task, str(err))
            return result(facts.task.id, SnapshotAnswer.UNAVAILABLE, str(err))
        self._finish(facts, _row(facts, payload, stored))
        self._retire_previous(facts, keep=stored.key)
        return result(facts.task.id, SnapshotAnswer.STORED)

    def unchanged(self, facts: Facts) -> SnapshotItemResult:
        """Record that the cleaned text did not change under the new artifact; no object is written."""
        self._index.refresh_artifact(page_key(facts.task), facts.item.artifact_sha256)
        complete_task(facts.task)
        return result(facts.task.id, SnapshotAnswer.UNCHANGED)

    def skipped(self, facts: Facts) -> SnapshotItemResult:
        """Write a marker that records the skip reason; the page has no object, and any old object is deleted."""
        item = facts.item
        assert item.skipped_reason is not None
        marker = SnapshotRowValues.skip_marker(item.artifact_sha256, item.source_hash, item.skipped_reason.value)
        self._finish(facts, marker)
        self._retire_previous(facts, keep=None)
        return result(facts.task.id, SnapshotAnswer.SKIPPED)

    def _finish(self, facts: Facts, values: SnapshotRowValues) -> None:
        self._index.upsert_row(page_key(facts.task), values)
        complete_task(facts.task)

    def _retire_previous(self, facts: Facts, keep: str | None) -> None:
        """Delete after commit the object the row pointed at before, unless it is the object just written."""
        previous = facts.existing.storage_key if facts.existing is not None else None
        if previous is not None and previous != keep:
            self._replaced.add(previous)
