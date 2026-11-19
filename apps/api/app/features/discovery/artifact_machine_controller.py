"""Machine HTTP handlers for artifacts: worker uploads and snapshot reads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from litestar import Controller, Response, get, post
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.params import Body, Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.features.discovery.artifact_list_query import provide_artifact_query
from app.features.discovery.artifact_policy import media_type, read_capped
from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.artifact_upload import ArtifactUpload, ArtifactUploadService
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.read_mappers import artifact_read
from app.features.discovery.repository import ArtifactFilter
from app.schema.discovery.artifacts import (
    ArtifactListResponse,
    ArtifactRead,
    ArtifactStatusResponse,
    ArtifactUploadForm,
    MissingScreenshotResponse,
)

MISSING_SCREENSHOT_LIMIT = 50


def _upload_from_form(form: ArtifactUploadForm) -> ArtifactUpload:
    return ArtifactUpload(
        kind=form.kind,
        content_type=media_type(form.file.content_type),
        data=read_capped(form.file.file),
        source_url=form.source_url,
        final_url=form.final_url,
        fetched_at=form.fetched_at or datetime.now(UTC),
    )


class DiscoveryArtifactMachineController(Controller):
    """Workers put page snapshots and screenshots into the object store through the API."""

    path = "/"
    guards = [require_discovery_machine]

    @post("/tasks/{task_id:uuid}/artifacts", sync_to_thread=True, status_code=HTTP_201_CREATED, guards=DB_WRITE_GUARDS)
    def upload_artifact(
        self,
        discovery_artifact_upload_service: ArtifactUploadService,
        task_id: UUID,
        data: Annotated[ArtifactUploadForm, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> Response[ArtifactRead]:
        """Store a worker's artifact for a task; an identical upload answers 200 with the existing row, not 201."""
        outcome = discovery_artifact_upload_service.upload(task_id, _upload_from_form(data))
        status = HTTP_201_CREATED if outcome.created else HTTP_200_OK
        return Response(artifact_read(outcome.artifact), status_code=status)

    @get("/artifacts/status", sync_to_thread=True)
    def artifact_status(self, discovery_artifact_read_service: ArtifactReadService) -> ArtifactStatusResponse:
        """Report whether uploads would be accepted: a store is set and the byte cap is not reached."""
        return discovery_artifact_read_service.status()

    @get("/artifacts/{artifact_id:uuid}/content", sync_to_thread=True)
    def artifact_content(
        self, discovery_artifact_read_service: ArtifactReadService, artifact_id: UUID
    ) -> Response[bytes]:
        """Return the stored bytes of one artifact with its recorded content type."""
        stored = discovery_artifact_read_service.content(artifact_id)
        return Response(stored.data, media_type=stored.content_type)

    @get("/artifacts/missing-screenshot", sync_to_thread=True)
    def missing_screenshot(
        self,
        discovery_artifact_read_service: ArtifactReadService,
        catalogue_service_id: UUID | None = Parameter(query="catalogue_service_id", default=None),
        limit: int = Parameter(query="limit", default=MISSING_SCREENSHOT_LIMIT, ge=1, le=100),
    ) -> MissingScreenshotResponse:
        """Page through rendered pages with no screenshot: the newest HTML snapshot of each, newest first."""
        return discovery_artifact_read_service.missing_screenshots(catalogue_service_id, limit)

    @get(
        "/artifacts",
        sync_to_thread=True,
        dependencies={"discovery_query": Provide(provide_artifact_query, sync_to_thread=False)},
    )
    def list_artifacts(
        self,
        discovery_artifact_read_service: ArtifactReadService,
        discovery_query: DiscoveryListQuery[ArtifactFilter],
    ) -> ArtifactListResponse:
        """Page through artifacts, optionally filtered by kind or host."""
        return discovery_artifact_read_service.list_artifacts(discovery_query.filters, discovery_query.page)
