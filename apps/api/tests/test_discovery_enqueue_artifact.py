"""Discovery task identity with an artifact: one artifact dedups, a new snapshot of the same page gets a fresh task."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import TaskQueue
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

PAGE_URL = "https://example.gov/leistung/anmeldung"
INPUT_KEY = "llm:0a1b2c3d"
NOTE = "docs=2 edges=1 dropped=0"


def _artifact(session: Session, catalogue: CatalogueService) -> DiscoveryArtifact:
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    artifact = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryArtifactKind.HTML_SNAPSHOT,
        storage_key=f"discovery/{catalogue.id}/html/{sha}",
        sha256=sha,
        content_type="text/html",
        byte_size=10,
        source_url=PAGE_URL,
        fetched_at=datetime.now(UTC),
    )
    session.add(artifact)
    session.flush()
    return artifact


def _target(catalogue: CatalogueService, artifact: DiscoveryArtifact | None) -> TaskTarget:
    return TaskTarget(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.LLM_EXTRACT,
        target_url=PAGE_URL,
        input_key=INPUT_KEY,
        artifact_id=None if artifact is None else artifact.id,
    )


def test_the_same_artifact_is_deduped_to_one_pending_task(db_session: Session) -> None:
    """discovery enqueue · a second enqueue with the same artifact_id returns the existing row."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    queue = TaskQueue(DiscoveryRepository(db_session))

    first = queue.enqueue(_target(catalogue, artifact))
    second = queue.enqueue(_target(catalogue, artifact))

    assert first.created is True
    assert second.created is False
    assert second.task.id == first.task.id


def test_a_new_artifact_for_the_same_page_gets_a_fresh_task(db_session: Session) -> None:
    """discovery enqueue · a re-rendered page (new artifact) gets a new task; the completed row keeps its note."""
    catalogue = _catalogue(db_session)
    old_artifact = _artifact(db_session, catalogue)
    new_artifact = _artifact(db_session, catalogue)
    queue = TaskQueue(DiscoveryRepository(db_session))
    done = queue.enqueue(_target(catalogue, old_artifact)).task
    done.status = DiscoveryTaskStatus.COMPLETED
    done.result_note = NOTE
    db_session.flush()

    fresh = queue.enqueue(_target(catalogue, new_artifact))

    assert fresh.created is True
    assert fresh.task.id != done.id
    assert fresh.task.artifact_id == new_artifact.id
    kept = db_session.get(DiscoveryTask, done.id)
    assert kept is not None
    assert (kept.status, kept.result_note, kept.artifact_id) == (DiscoveryTaskStatus.COMPLETED, NOTE, old_artifact.id)


def test_a_target_without_an_artifact_keeps_the_old_identity(db_session: Session) -> None:
    """discovery enqueue · an artifact-less enqueue still matches an existing open or completed task of the page."""
    catalogue = _catalogue(db_session)
    artifact = _artifact(db_session, catalogue)
    queue = TaskQueue(DiscoveryRepository(db_session))
    existing = queue.enqueue(_target(catalogue, artifact)).task

    repeat = queue.enqueue(_target(catalogue, None))

    assert repeat.created is False
    assert repeat.task.id == existing.id
