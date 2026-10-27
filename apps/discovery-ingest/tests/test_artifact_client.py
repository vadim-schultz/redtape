"""Machine client routes the render worker needs: release, complete with a note, artifact upload and status."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.artifacts import ArtifactUpload

API_BASE = "https://redtape.test"
TASK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]
FETCHED_AT = datetime(2026, 10, 27, 9, 30, tzinfo=UTC)


def _client(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> DiscoveryMachineClient:
    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
    return DiscoveryMachineClient(API_BASE, "test-machine-key")


def _artifact_json() -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "catalogue_service_id": str(uuid.uuid4()),
        "discovery_task_id": str(TASK_ID),
        "kind": "html_snapshot",
        "storage_key": "discovery/x/html_snapshot/abc.html",
        "sha256": "abc",
        "content_type": "text/html",
        "byte_size": 12,
        "source_url": "https://portal.example/s",
        "final_url": "https://portal.example/s",
        "fetched_at": FETCHED_AT.isoformat(),
        "created_at": FETCHED_AT.isoformat(),
    }


def _upload(final_url: str | None = "https://portal.example/final") -> ArtifactUpload:
    return ArtifactUpload(
        kind="html_snapshot",
        data="<p>Bürger</p>".encode(),
        content_type="text/html",
        source_url="https://portal.example/s",
        final_url=final_url,
        fetched_at=FETCHED_AT,
    )


def test_release_posts_the_reason_and_the_optional_not_before(monkeypatch: pytest.MonkeyPatch) -> None:
    """client · release_task posts {reason} and {reason, not_before} to the release route."""
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(f"/machine/tasks/{TASK_ID}/release")
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"id": str(TASK_ID), "status": "pending", "last_error": "x"})

    client = _client(monkeypatch, handler)
    client.release_task(TASK_ID, "browser_quota")
    client.release_task(TASK_ID, "browser_quota", not_before=FETCHED_AT)

    assert bodies == [{"reason": "browser_quota"}, {"reason": "browser_quota", "not_before": FETCHED_AT.isoformat()}]


def test_release_of_a_task_that_is_not_claimed_raises_the_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """client · a 409 on release is a DiscoveryMachineApiError, not a silent success."""
    client = _client(monkeypatch, lambda request: httpx.Response(409, text="task is not claimed"))

    with pytest.raises(DiscoveryMachineApiError) as caught:
        client.release_task(TASK_ID, "x")

    assert caught.value.status_code == 409


def test_complete_sends_the_note_only_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """client · complete_task posts {note} with a note and no body without one."""
    seen: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.content)
        return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed"})

    client = _client(monkeypatch, handler)
    client.complete_task(TASK_ID)
    client.complete_task(TASK_ID, note="login_wall")

    assert seen[0] == b"" and json.loads(seen[1]) == {"note": "login_wall"}


def test_upload_sends_a_multipart_form_and_reports_created_or_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """client · upload_artifact posts file and fields; 201 is created, 200 is an existing identical artifact."""
    requests: list[httpx.Request] = []
    statuses = iter([201, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(next(statuses), json=_artifact_json())

    client = _client(monkeypatch, handler)
    created = client.upload_artifact(TASK_ID, _upload())
    existing = client.upload_artifact(TASK_ID, _upload(final_url=None))

    first = requests[0]
    assert first.url.path.endswith(f"/machine/tasks/{TASK_ID}/artifacts")
    assert first.headers["content-type"].startswith("multipart/form-data")
    for part in (
        'name="kind"',
        "html_snapshot",
        'name="source_url"',
        'name="final_url"',
        "https://portal.example/final",
    ):
        assert part in first.content.decode()
    assert "Bürger".encode() in first.content and 'name="final_url"' not in requests[1].content.decode()
    assert (created.created, existing.created) == (True, False)
    assert created.artifact.kind == "html_snapshot" and created.artifact.byte_size == 12


@pytest.mark.parametrize(
    ("status", "detail"), [(503, "object store is not configured"), (507, "object store byte cap")]
)
def test_upload_raises_the_api_error_for_a_storage_problem(
    monkeypatch: pytest.MonkeyPatch, status: int, detail: str
) -> None:
    """client · 503 and 507 raise with the status; only database_soft_limit counts as a database limit."""
    client = _client(monkeypatch, lambda request: httpx.Response(status, text=detail))

    with pytest.raises(DiscoveryMachineApiError) as caught:
        client.upload_artifact(TASK_ID, _upload())

    assert (caught.value.status_code, caught.value.is_database_limit) == (status, False)


def test_artifact_status_reads_the_storage_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """client · get_artifact_status returns storage_enabled and the byte accounting."""
    body = {"storage_enabled": True, "bytes_used": 10, "bytes_cap": 100}
    client = _client(monkeypatch, lambda request: httpx.Response(200, json=body))

    status = client.get_artifact_status()

    assert (status.storage_enabled, status.bytes_used, status.bytes_cap) == (True, 10, 100)
