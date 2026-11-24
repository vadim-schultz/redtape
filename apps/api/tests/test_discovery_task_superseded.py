"""Superseded extractions: a completed task under an older input key is re-pended under the current key, once per page (chapter 5, loop D)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import SupersededResult, TaskQueue
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
CURRENT = "llm:cur00001"
OLD = "llm:old00005"
HASH = "a" * 64


def _artifact(session: Session, catalogue: CatalogueService) -> DiscoveryArtifact:
    artifact = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryArtifactKind.HTML_SNAPSHOT,
        storage_key=f"artifacts/{uuid.uuid4().hex}.html",
        sha256=uuid.uuid4().hex * 2,
        content_type="text/html",
        byte_size=2048,
        source_url="https://example.gov/service",
        final_url=None,
        fetched_at=NOW,
    )
    session.add(artifact)
    session.flush()
    return artifact


def _task(
    session: Session,
    catalogue: CatalogueService,
    *,
    url: str,
    status: DiscoveryTaskStatus,
    input_key: str | None,
    artifact: DiscoveryArtifact | None,
    kind: DiscoveryTaskKind = DiscoveryTaskKind.LLM_EXTRACT,
) -> DiscoveryTask:
    """Insert one llm_extract task for ``url`` in ``status`` under ``input_key``, with ``artifact`` when given."""
    target = TaskTarget(
        catalogue_service_id=catalogue.id,
        kind=kind,
        target_url=url,
        input_key=input_key,
        artifact_id=artifact.id if artifact else None,
    )
    task = DiscoveryRepository(session).insert_task(target)
    task.status = status
    task.attempt_count = 2
    task.result_note = "docs=2 edges=1 dropped=0"
    task.text_hash = HASH
    session.flush()
    return task


def _completed(
    session: Session,
    catalogue: CatalogueService,
    *,
    url: str,
    input_key: str | None,
    artifact: DiscoveryArtifact | None,
) -> DiscoveryTask:
    return _task(
        session,
        catalogue,
        url=url,
        status=DiscoveryTaskStatus.COMPLETED,
        input_key=input_key,
        artifact=artifact,
    )


def _row(session: Session, task_id: uuid.UUID) -> DiscoveryTask:
    row = session.get(DiscoveryTask, task_id)
    assert row is not None
    return row


def _requeue(session: Session, *, limit: int = 50, dry_run: bool = False) -> SupersededResult:
    queue = TaskQueue(DiscoveryRepository(session))
    return queue.requeue_superseded(kind=DiscoveryTaskKind.LLM_EXTRACT, input_key=CURRENT, limit=limit, dry_run=dry_run)


def test_a_completed_extraction_under_an_older_key_is_repended_under_the_current_key(db_session: Session) -> None:
    """superseded requeue · happy: one ext-5 row is pending again under the current key, with its attempts and note cleared and its artifact kept."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    old = _completed(db_session, catalogue, url="https://example.gov/a", input_key=OLD, artifact=artifact)

    result = _requeue(db_session)

    row = _row(db_session, old.id)
    assert (result.matched, result.requeued) == (1, 1)
    assert (row.status, row.input_key, row.attempt_count) == (DiscoveryTaskStatus.PENDING, CURRENT, 0)
    assert (row.result_note, row.text_hash, row.artifact_id) == (None, None, artifact.id)


def test_rows_already_under_the_current_key_or_without_an_artifact_or_not_completed_stay_as_they_are(
    db_session: Session,
) -> None:
    """superseded requeue · negative: a current-key completion, an old row with no artifact, a failed old row and another kind are all left alone."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    kept = [
        _completed(db_session, catalogue, url="https://example.gov/current", input_key=CURRENT, artifact=artifact),
        _completed(db_session, catalogue, url="https://example.gov/no-artifact", input_key=OLD, artifact=None),
        _task(
            db_session,
            catalogue,
            url="https://example.gov/failed",
            status=DiscoveryTaskStatus.FAILED,
            input_key=OLD,
            artifact=artifact,
        ),
        _task(
            db_session,
            catalogue,
            url="https://example.gov/fetch",
            status=DiscoveryTaskStatus.COMPLETED,
            input_key=OLD,
            artifact=artifact,
            kind=DiscoveryTaskKind.FETCH_URL,
        ),
    ]

    result = _requeue(db_session)

    assert (result.matched, result.requeued) == (0, 0)
    assert [(_row(db_session, task.id).status, _row(db_session, task.id).input_key) for task in kept] == [
        (DiscoveryTaskStatus.COMPLETED, CURRENT),
        (DiscoveryTaskStatus.COMPLETED, OLD),
        (DiscoveryTaskStatus.FAILED, OLD),
        (DiscoveryTaskStatus.COMPLETED, OLD),
    ]


def test_a_page_that_already_has_a_task_under_the_current_key_is_not_requeued(db_session: Session) -> None:
    """superseded requeue · negative: the page has a pending current-key task, so the old row is left for it (no duplicate identity)."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    old = _completed(db_session, catalogue, url="https://example.gov/b", input_key=OLD, artifact=artifact)
    _task(
        db_session,
        catalogue,
        url="https://example.gov/b",
        status=DiscoveryTaskStatus.PENDING,
        input_key=CURRENT,
        artifact=artifact,
    )

    result = _requeue(db_session)

    assert (result.matched, result.requeued) == (0, 0)
    assert _row(db_session, old.id).input_key == OLD


def test_two_old_rows_for_one_page_requeue_once_and_a_second_run_finds_nothing(db_session: Session) -> None:
    """superseded requeue · negative: two superseded rows for one page yield one re-pended row; a second run matches nothing."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    _completed(db_session, catalogue, url="https://example.gov/c", input_key=OLD, artifact=artifact)
    _completed(db_session, catalogue, url="https://example.gov/c", input_key="llm:old00004", artifact=artifact)

    first = _requeue(db_session)
    second = _requeue(db_session)

    assert (first.matched, first.requeued) == (1, 1)
    assert (second.matched, second.requeued) == (0, 0)


def test_a_dry_run_counts_the_superseded_pages_and_changes_nothing(db_session: Session) -> None:
    """superseded requeue · negative: dry_run counts the match and leaves the old row completed under its key."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    old = _completed(db_session, catalogue, url="https://example.gov/d", input_key=OLD, artifact=artifact)

    result = _requeue(db_session, dry_run=True)

    row = _row(db_session, old.id)
    assert (result.matched, result.requeued) == (1, 0)
    assert (row.status, row.input_key) == (DiscoveryTaskStatus.COMPLETED, OLD)


def test_the_limit_bounds_how_many_pages_are_repended_in_one_call(db_session: Session) -> None:
    """superseded requeue · happy: three superseded pages and a limit of two re-pend two; the third waits for the next call."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    for number in range(3):
        _completed(db_session, catalogue, url=f"https://example.gov/limit/{number}", input_key=OLD, artifact=artifact)

    first = _requeue(db_session, limit=2)
    second = _requeue(db_session, limit=2)

    assert (first.matched, first.requeued) == (2, 2)
    assert (second.matched, second.requeued) == (1, 1)
