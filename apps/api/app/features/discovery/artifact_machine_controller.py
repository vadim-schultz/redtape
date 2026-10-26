"""Machine HTTP handlers for artifacts: worker uploads and snapshot reads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from litestar import Controller, Response, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.features.discovery.artifact_policy import media_type, read_capped
from app.features.discovery.artifact_upload import ArtifactUpload, ArtifactUploadService
from app.features.discovery.guards import require_discovery_machine
from app.schema.discovery.artifacts import ArtifactRead, ArtifactUploadForm


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

    @post("/tasks/{task_id:uuid}/artifacts", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def upload_artifact(
        self,
        discovery_artifact_upload_service: ArtifactUploadService,
        task_id: UUID,
        data: Annotated[ArtifactUploadForm, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> Response[ArtifactRead]:
        outcome = discovery_artifact_upload_service.upload(task_id, _upload_from_form(data))
        status = HTTP_201_CREATED if outcome.created else HTTP_200_OK
        return Response(ArtifactRead.from_row(outcome.artifact), status_code=status)
