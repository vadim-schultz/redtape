"""Accept an artifact from a worker: validate, deduplicate by hash, cap, store, record, prune."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.features.discovery.artifact_policy import KEEP_LATEST_SNAPSHOTS, extension_for, storage_key
from app.features.discovery.errors import StorageCapExceededError
from app.features.discovery.lookups import require_task
from app.features.discovery.repository import DiscoveryRepository, NewArtifact
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind, DiscoveryTask
from app.shared.object_store import ObjectStore, ObjectStoreError
from app.shared.object_store.provider import require_store

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ArtifactUpload:
    """What a worker sent: the bytes, their declared media type and where they came from."""

    kind: DiscoveryArtifactKind
    content_type: str
    data: bytes
    source_url: str
    final_url: str | None
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """The artifact behind an upload and whether this call created it."""

    artifact: DiscoveryArtifact
    created: bool


class ArtifactUploadService:
    """Store worker uploads in the object store and record their metadata."""

    def __init__(self, repository: DiscoveryRepository, store: ObjectStore | None, *, max_bytes: int) -> None:
        """Bind the service to ``repository``, an optional ``store`` and the byte cap ``max_bytes``."""
        self._repo = repository
        self._store = store
        self._max_bytes = max_bytes

    def upload(self, task_id: UUID, upload: ArtifactUpload) -> UploadOutcome:
        """Store ``upload`` for the catalogue row of ``task_id``; an identical artifact returns the existing row."""
        task = require_task(self._repo, task_id)
        extension = extension_for(upload.kind, upload.content_type, len(upload.data))
        store = require_store(self._store)
        new = _new_artifact(task, upload, extension)
        existing = self._repo.find_artifact(new.catalogue_service_id, new.kind, new.sha256)
        if existing is not None:
            return UploadOutcome(existing, created=False)
        self._ensure_headroom(new.byte_size)
        store.put(new.storage_key, upload.data, new.content_type)
        return UploadOutcome(self._record(store, new), created=True)

    def _ensure_headroom(self, incoming: int) -> None:
        if self._repo.total_artifact_bytes() + incoming > self._max_bytes:
            raise StorageCapExceededError("Artifact storage cap reached")

    def _record(self, store: ObjectStore, new: NewArtifact) -> DiscoveryArtifact:
        row = self._repo.insert_artifact(new)
        if new.kind is DiscoveryArtifactKind.HTML_SNAPSHOT:
            self._prune(store, new.catalogue_service_id)
        return row

    def _prune(self, store: ObjectStore, catalogue_id: UUID) -> None:
        for key in self._repo.delete_old_snapshots(catalogue_id, keep=KEEP_LATEST_SNAPSHOTS):
            _delete_object(store, key)


def _delete_object(store: ObjectStore, key: str) -> None:
    try:
        store.delete(key)
    except ObjectStoreError:
        logger.warning("orphaned artifact object left in the store: %s", key)


def _new_artifact(task: DiscoveryTask, upload: ArtifactUpload, extension: str) -> NewArtifact:
    sha256 = hashlib.sha256(upload.data).hexdigest()
    return NewArtifact(
        catalogue_service_id=task.catalogue_service_id,
        discovery_task_id=task.id,
        kind=upload.kind,
        storage_key=storage_key(task.catalogue_service_id, upload.kind, sha256, extension),
        sha256=sha256,
        content_type=upload.content_type,
        byte_size=len(upload.data),
        source_url=upload.source_url,
        final_url=upload.final_url,
        fetched_at=upload.fetched_at,
    )
