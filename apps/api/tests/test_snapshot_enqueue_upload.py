"""A new snapshot refreshes only the page translations already stored or queued; an identical sha changes nothing (chapter 09)."""

from __future__ import annotations

import hashlib
import inspect
from datetime import UTC, datetime

from app.config import settings
from app.features.discovery.artifact_upload import ArtifactUpload, ArtifactUploadService, UploadOutcome
from app.features.discovery.dependencies import provide_discovery_artifact_upload_service
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import CatalogueService, DiscoveryArtifactKind, DiscoveryTaskKind
from app.models.search import WorkTaskStatus
from app.shared.object_store import InMemoryObjectStore
from sqlalchemy.orm import Session

from snapshot_machine_support import SHA_A, add_snapshot, stored_row, task_in_state, task_rows
from test_discovery_admin_api import _catalogue, _kind_task

FETCHED_AT = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
NEW_HTML = b"<html><body>neue Fassung</body></html>"
NEW_SHA = hashlib.sha256(NEW_HTML).hexdigest()


def _upload(session: Session, catalogue: CatalogueService, data: bytes = NEW_HTML) -> UploadOutcome:
    task = _kind_task(session, catalogue, DiscoveryTaskKind.FETCH_URL)
    service = provide_discovery_artifact_upload_service(DiscoveryRepository(session), InMemoryObjectStore())
    return service.upload(
        task.id,
        ArtifactUpload(
            kind=DiscoveryArtifactKind.HTML_SNAPSHOT,
            content_type="text/html",
            data=data,
            source_url="https://example.gov/page",
            final_url=None,
            fetched_at=FETCHED_AT,
        ),
    )


def test_a_new_snapshot_for_a_translated_page_refreshes_its_task_to_pending(db_session: Session) -> None:
    catalogue = _catalogue(db_session, external_id="svc-translated")
    add_snapshot(db_session, catalogue, SHA_A)
    stored_row(db_session, catalogue, "en", artifact_sha=SHA_A)

    _upload(db_session, catalogue)

    (task,) = task_rows(db_session, catalogue.id, "en")
    assert (task.status, task.source_hash) == (WorkTaskStatus.PENDING, NEW_SHA)
    assert task_rows(db_session, catalogue.id, "tr") == []


def test_a_new_snapshot_for_a_queued_page_refreshes_its_open_task_only(db_session: Session) -> None:
    catalogue = _catalogue(db_session, external_id="svc-queued")
    add_snapshot(db_session, catalogue, SHA_A)
    task_in_state(db_session, catalogue, WorkTaskStatus.PENDING, "tr", source_hash=SHA_A)

    _upload(db_session, catalogue)

    (task,) = task_rows(db_session, catalogue.id, "tr")
    assert (task.status, task.source_hash) == (WorkTaskStatus.PENDING, NEW_SHA)
    assert task_rows(db_session, catalogue.id, "en") == []


def test_a_new_snapshot_for_a_page_with_no_candidates_and_no_translation_enqueues_nothing(
    db_session: Session,
) -> None:
    catalogue = _catalogue(db_session, external_id="svc-idle")

    outcome = _upload(db_session, catalogue)

    assert outcome.created
    assert all(task_rows(db_session, catalogue.id, locale) == [] for locale in settings.translation_target_locale_codes)


def test_an_identical_sha_returns_the_existing_row_and_enqueues_nothing(db_session: Session) -> None:
    catalogue = _catalogue(db_session, external_id="svc-repeat")
    first = _upload(db_session, catalogue)
    stored_row(db_session, catalogue, "en", artifact_sha=NEW_SHA)

    second = _upload(db_session, catalogue)

    assert (second.created, second.artifact.id) == (False, first.artifact.id)
    assert task_rows(db_session, catalogue.id, "en") == []


def test_the_upload_service_takes_the_repository_the_store_and_one_policy() -> None:
    parameters = list(inspect.signature(ArtifactUploadService.__init__).parameters)

    assert parameters == ["self", "repository", "store", "policy"]
