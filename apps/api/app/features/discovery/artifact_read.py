"""Read artifacts: stream bytes to workers, list metadata, mint download URLs for admins."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.discovery.errors import ArtifactNotFoundError
from app.features.discovery.lookups import require_artifact, require_candidate, require_catalogue
from app.features.discovery.repository import ArtifactFilter, DiscoveryRepository, Page
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind
from app.schema.discovery.artifacts import (
    AdminArtifactListResponse,
    AdminArtifactRead,
    ArtifactListResponse,
    ArtifactRead,
    ArtifactStatusResponse,
)
from app.shared.object_store import ObjectNotFoundError, ObjectStore, ObjectStoreMeter, noop_meter
from app.shared.object_store.provider import require_store


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    """Stored bytes with the content type they were uploaded with."""

    content_type: str
    data: bytes


class ArtifactReadService:
    """Serve artifact bytes and metadata."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        store: ObjectStore | None,
        *,
        max_bytes: int,
        presign_meter: ObjectStoreMeter = noop_meter,
    ) -> None:
        """Bind the service to ``repository``, an optional ``store``, the byte cap and the ``presign_meter``.

        Presigned URLs are served by the object store itself, so the store never sees them; ``presign_meter``
        counts each URL as one read.
        """
        self._repo = repository
        self._store = store
        self._max_bytes = max_bytes
        self._presign_meter = presign_meter

    def content(self, artifact_id: UUID) -> ArtifactContent:
        """Return the bytes of one artifact; raise a 404 when the row or its object is missing, 503 without a store."""
        artifact = require_artifact(self._repo, artifact_id)
        store = require_store(self._store)
        try:
            return ArtifactContent(artifact.content_type, store.get(artifact.storage_key))
        except ObjectNotFoundError as err:
            raise ArtifactNotFoundError() from err

    def list_artifacts(self, artifact_filter: ArtifactFilter, page: Page) -> ArtifactListResponse:
        """Return one page of artifact metadata matching ``artifact_filter``."""
        rows, total = self._page_of(artifact_filter, page)
        items = [ArtifactRead.from_row(row) for row in rows]
        return ArtifactListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def list_for_catalogue(self, catalogue_id: UUID, page: Page) -> AdminArtifactListResponse:
        """Return one page of a catalogue row's artifacts, each with a presigned download URL."""
        require_catalogue(self._repo, catalogue_id)
        rows, total = self._page_of(ArtifactFilter(catalogue_service_id=catalogue_id), page)
        return self._with_urls(rows, total, page)

    def list_for_candidate(self, candidate_id: UUID, page: Page) -> AdminArtifactListResponse:
        """Return one page of the evidence behind a candidate, each artifact with a presigned download URL.

        Evidence is every artifact a mention cites plus the latest screenshot of each procedure that mentions it.
        """
        require_candidate(self._repo, candidate_id)
        rows = self._repo.list_candidate_artifacts_page(candidate_id, page)
        return self._with_urls(rows, self._repo.count_candidate_artifacts(candidate_id), page)

    def status(self) -> ArtifactStatusResponse:
        """Report whether uploads would be accepted: a store is set and the byte cap is not reached."""
        used = self._repo.total_artifact_bytes()
        enabled = self._store is not None and used < self._max_bytes
        return ArtifactStatusResponse(storage_enabled=enabled, bytes_used=used, bytes_cap=self._max_bytes)

    def _page_of(self, artifact_filter: ArtifactFilter, page: Page) -> tuple[list[DiscoveryArtifact], int]:
        rows = self._repo.list_artifacts_page(artifact_filter, page)
        return rows, self._repo.count_artifacts(artifact_filter)

    def _with_urls(self, rows: list[DiscoveryArtifact], total: int, page: Page) -> AdminArtifactListResponse:
        self._count_presigned_reads(len(rows))
        items = [self._with_url(row) for row in rows]
        return AdminArtifactListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def _count_presigned_reads(self, urls: int) -> None:
        """Reserve one Class B operation per URL about to be minted; a denial raises before any URL exists."""
        if self._store is not None and urls:
            self._presign_meter("class_b", urls)

    def _with_url(self, row: DiscoveryArtifact) -> AdminArtifactRead:
        return AdminArtifactRead(**ArtifactRead.from_row(row).model_dump(), url=self._presign(row))

    def _presign(self, row: DiscoveryArtifact) -> str | None:
        if self._store is None:
            return None
        return self._store.presigned_get_url(row.storage_key, download_name=_download_name(row))


def _download_name(row: DiscoveryArtifact) -> str | None:
    """Name HTML snapshots so the browser downloads them; images open inline."""
    if row.kind is not DiscoveryArtifactKind.HTML_SNAPSHOT:
        return None
    return row.storage_key.rsplit("/", 1)[-1]
