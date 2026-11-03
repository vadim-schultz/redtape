"""Artifact routes: upload a snapshot or screenshot for a task, read storage status, download bytes and list metadata."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.artifacts import (
    ArtifactContent,
    ArtifactPage,
    ArtifactQuery,
    ArtifactRead,
    ArtifactStatus,
    ArtifactUpload,
    StoredArtifact,
)
from discovery_ingest.client.http_client import MachineHttpClient

HTTP_CREATED = 201


class ArtifactsAPI:
    """Store, read and list artifacts; the upload route hangs under a task, the rest under the artifact store."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def upload(self, task_id: UUID, upload: ArtifactUpload) -> StoredArtifact:
        """Store a snapshot or screenshot for a claimed task; 201 created it, 200 matched identical stored bytes."""
        fields = {"kind": upload.kind, "source_url": upload.source_url, "fetched_at": upload.fetched_at.isoformat()}
        if upload.final_url:
            fields["final_url"] = upload.final_url
        files = {"file": (f"{upload.kind}", upload.data, upload.content_type)}
        response = self._http.request("POST", f"/tasks/{task_id}/artifacts", data=fields, files=files)
        return StoredArtifact(ArtifactRead.model_validate(response.json()), response.status_code == HTTP_CREATED)

    def status(self) -> ArtifactStatus:
        """Report whether storage is configured, with bytes used against the cap."""
        return self._http.request_model(ArtifactStatus, "GET", "/artifacts/status")

    def content(self, artifact_id: UUID) -> ArtifactContent:
        """Download the stored bytes of ``artifact_id``; 404 means unknown or missing object, 503 an unset store."""
        response = self._http.request("GET", f"/artifacts/{artifact_id}/content")
        return ArtifactContent(response.content, response.headers.get("content-type"))

    def list(self, query: ArtifactQuery) -> ArtifactPage:
        """List stored artifacts matching ``query``, newest first; ``limit`` is at most 100."""
        params: dict[str, str | int] = {"kind": query.kind, "offset": query.offset, "limit": query.limit}
        if query.host is not None:
            params["host"] = query.host
        return self._http.request_model(ArtifactPage, "GET", "/artifacts", params=params)
