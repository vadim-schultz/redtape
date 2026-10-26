"""HTTP behavior of the artifact upload, read and status routes (chapter 14)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.models.discovery import DiscoveryArtifact, DiscoveryTask, DiscoveryTaskKind
from app.shared.dependencies import shared_dependencies
from app.shared.object_store import InMemoryObjectStore, ObjectStore
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _admin_headers, _catalogue, _kind_task
from test_discovery_machine_api import _issue_key

MACHINE = "/api/v1/discovery/machine"
HTML = b"<html><body>rendered</body></html>"
PNG = b"\x89PNG\r\n\x1a\n" + b"screenshot"
FETCHED_AT = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


class StoreSlot:
    """The store the test app resolves for its ``object_store`` dependency; tests may swap or clear it."""

    def __init__(self) -> None:
        self.store: ObjectStore | None = InMemoryObjectStore()

    @property
    def memory(self) -> InMemoryObjectStore:
        assert isinstance(self.store, InMemoryObjectStore)
        return self.store


class ExplodingStore:
    """A store that fails on any operation, proving a route never reached it."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        raise AssertionError("put")

    def get(self, key: str) -> bytes:
        raise AssertionError("get")

    def exists(self, key: str) -> bool:
        raise AssertionError("exists")

    def delete(self, key: str) -> None:
        raise AssertionError("delete")

    def presigned_get_url(self, key: str, *, expires_in: int = 300, download_name: str | None = None) -> str:
        raise AssertionError("presign")


@pytest.fixture
def slot(monkeypatch: pytest.MonkeyPatch) -> StoreSlot:
    holder = StoreSlot()
    monkeypatch.setitem(shared_dependencies, "object_store", Provide(lambda: holder.store, sync_to_thread=False))
    return holder


@pytest.fixture
def client(slot: StoreSlot, client: TestClient[Litestar]) -> TestClient[Litestar]:  # noqa: F811
    """The shared admin and machine test client, built after the store override is in place."""
    return client


def _upload_url(task_id: uuid.UUID) -> str:
    return f"{MACHINE}/tasks/{task_id}/artifacts"


def _upload(
    client: TestClient[Litestar],
    key: str,
    task_id: uuid.UUID,
    *,
    content: bytes = HTML,
    content_type: str = "text/html",
    **fields: str,
):
    form = {"kind": "html_snapshot", "source_url": "https://example.gov/page", "fetched_at": FETCHED_AT.isoformat()}
    return client.post(
        _upload_url(task_id),
        files={"file": ("artifact", content, content_type)},
        data={**form, **fields},
        headers={"X-API-Key": key},
    )


def _task(db_session: Session, external_id: str = "svc-1") -> DiscoveryTask:
    return _kind_task(db_session, _catalogue(db_session, external_id=external_id), DiscoveryTaskKind.FETCH_URL)


def _artifacts(db_session: Session, catalogue_id: uuid.UUID) -> list[DiscoveryArtifact]:
    stmt = select(DiscoveryArtifact).where(DiscoveryArtifact.catalogue_service_id == catalogue_id)
    return list(db_session.scalars(stmt.order_by(DiscoveryArtifact.fetched_at)).all())


def test_upload_stores_bytes_under_the_content_addressed_key_and_returns_201(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    response = _upload(client, key, task.id, final_url="https://example.gov/final")

    sha = hashlib.sha256(HTML).hexdigest()
    storage_key = f"discovery/{task.catalogue_service_id}/html_snapshot/{sha}.html"
    assert response.status_code == 201
    assert slot.memory.get(storage_key) == HTML
    assert slot.memory.content_type(storage_key) == "text/html"
    body = response.json()
    assert (body["sha256"], body["byte_size"], body["kind"]) == (sha, len(HTML), "html_snapshot")
    assert (body["final_url"], body["discovery_task_id"]) == ("https://example.gov/final", str(task.id))
    assert [row.storage_key for row in _artifacts(db_session, task.catalogue_service_id)] == [storage_key]


def test_screenshot_keys_use_png_and_jpg_extensions(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    png = _upload(client, key, task.id, content=PNG, content_type="image/png", kind="screenshot")
    jpg = _upload(client, key, task.id, content=b"jpeg", content_type="image/jpeg", kind="screenshot")

    assert png.json()["storage_key"].endswith(".png")
    assert jpg.json()["storage_key"].endswith(".jpg")


def test_identical_upload_returns_200_and_the_same_artifact_id(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    first = _upload(client, key, task.id)
    second = _upload(client, key, task.id)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert len(_artifacts(db_session, task.catalogue_service_id)) == 1


def test_server_ignores_a_client_supplied_hash(client: TestClient[Litestar], db_session: Session) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    response = _upload(client, key, task.id, sha256="f" * 64)

    assert response.status_code == 201
    assert response.json()["sha256"] == hashlib.sha256(HTML).hexdigest()
    assert "f" * 64 not in response.json()["storage_key"]


@pytest.mark.parametrize(
    ("kind", "content_type", "size", "status"),
    [
        ("html_snapshot", "image/png", 10, 415),
        ("screenshot", "text/html", 10, 415),
        ("html_snapshot", "text/html", 4 * 1024 * 1024 + 1, 413),
        ("screenshot", "image/png", 8 * 1024 * 1024 + 1, 413),
    ],
)
def test_upload_rejects_a_wrong_content_type_and_an_oversize_file(
    client: TestClient[Litestar],
    slot: StoreSlot,
    db_session: Session,
    kind: str,
    content_type: str,
    size: int,
    status: int,
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    response = _upload(client, key, task.id, content=b"x" * size, content_type=content_type, kind=kind)

    assert response.status_code == status
    assert _artifacts(db_session, task.catalogue_service_id) == []
    assert slot.memory.stored_keys() == []


def test_upload_for_an_unknown_task_is_404(client: TestClient[Litestar], db_session: Session) -> None:
    key = _issue_key(db_session)

    response = _upload(client, key, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["detail"] == "Discovery task not found"


def test_upload_requires_the_machine_key(client: TestClient[Litestar], db_session: Session) -> None:
    task = _task(db_session)

    assert _upload(client, "wrong", task.id).status_code == 401


def test_upload_returns_503_and_writes_no_row_when_the_store_is_unset(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    slot.store = None

    response = _upload(client, key, task.id)

    assert response.status_code == 503
    assert _artifacts(db_session, task.catalogue_service_id) == []


def _snapshot(client: TestClient[Litestar], key: str, task_id: uuid.UUID, n: int) -> str:
    response = _upload(
        client,
        key,
        task_id,
        content=f"<html>{n}</html>".encode(),
        fetched_at=(FETCHED_AT + timedelta(minutes=n)).isoformat(),
    )
    return response.json()["storage_key"]


def test_third_snapshot_prunes_the_oldest_row_and_object(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    keys = [_snapshot(client, key, task.id, n) for n in (1, 2, 3)]

    assert [row.storage_key for row in _artifacts(db_session, task.catalogue_service_id)] == keys[1:]
    assert slot.memory.exists(keys[0]) is False
    assert slot.memory.exists(keys[1]) and slot.memory.exists(keys[2])


def test_screenshots_are_never_pruned(client: TestClient[Litestar], slot: StoreSlot, db_session: Session) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    for n in range(4):
        content = PNG + bytes([n])
        _upload(client, key, task.id, content=content, content_type="image/png", kind="screenshot")

    assert len(_artifacts(db_session, task.catalogue_service_id)) == 4


def test_upload_over_the_byte_cap_returns_507_and_writes_nothing(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    monkeypatch.setattr(settings, "object_store_max_bytes", len(HTML) + 5)
    assert _upload(client, key, task.id).status_code == 201

    over = _upload(client, key, task.id, content=b"<html>second</html>")

    assert over.status_code == 507
    assert len(_artifacts(db_session, task.catalogue_service_id)) == 1
    assert len(slot.memory.stored_keys()) == 1


def test_an_identical_reupload_under_a_full_cap_still_returns_200(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    monkeypatch.setattr(settings, "object_store_max_bytes", len(HTML))
    assert _upload(client, key, task.id).status_code == 201

    assert _upload(client, key, task.id).status_code == 200


def test_a_reupload_of_an_existing_sha256_makes_no_store_call(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    assert _upload(client, key, task.id).status_code == 201
    slot.store = ExplodingStore()

    again = _upload(client, key, task.id)

    assert again.status_code == 200
    stored = db_session.scalar(select(func.count()).select_from(DiscoveryArtifact))
    assert stored == 1


def _stored(
    client: TestClient[Litestar],
    key: str,
    task: DiscoveryTask,
    *,
    content: bytes = HTML,
    kind: str = "html_snapshot",
    content_type: str = "text/html",
    **fields: str,
) -> dict[str, str]:
    response = _upload(client, key, task.id, content=content, content_type=content_type, kind=kind, **fields)
    assert response.status_code == 201
    return response.json()


def _admin_list_url(catalogue_id: uuid.UUID) -> str:
    return f"/api/v1/discovery/admin/catalogue/{catalogue_id}/artifacts"


def test_content_route_returns_the_exact_bytes_and_content_type(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task, content=PNG, kind="screenshot", content_type="image/png")

    response = client.get(f"{MACHINE}/artifacts/{artifact['id']}/content", headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"


def test_content_route_is_404_for_an_unknown_artifact_and_503_when_the_store_is_unset(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)
    slot.store = None

    unknown = client.get(f"{MACHINE}/artifacts/{uuid.uuid4()}/content", headers={"X-API-Key": key})
    unset = client.get(f"{MACHINE}/artifacts/{artifact['id']}/content", headers={"X-API-Key": key})

    assert (unknown.status_code, unset.status_code) == (404, 503)
    assert unknown.json()["detail"] == "Discovery artifact not found"


def test_content_route_is_404_when_the_object_is_missing_from_the_store(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)
    slot.memory.delete(artifact["storage_key"])

    response = client.get(f"{MACHINE}/artifacts/{artifact['id']}/content", headers={"X-API-Key": key})

    assert response.status_code == 404
    assert response.json()["detail"] == "Discovery artifact not found"


def test_admin_list_returns_presigned_urls_and_html_urls_carry_an_attachment_disposition(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    html = _stored(client, key, task)
    shot = _stored(client, key, task, content=PNG, kind="screenshot", content_type="image/png")

    response = client.get(_admin_list_url(task.catalogue_service_id), headers=_admin_headers())

    assert response.status_code == 200
    urls = {item["id"]: item["url"] for item in response.json()["items"]}
    assert urls[html["id"]].startswith("memory://") and "expires_in=300" in urls[html["id"]]
    assert "attachment" in urls[html["id"]]
    assert "attachment" not in urls[shot["id"]]


def test_admin_list_returns_metadata_with_a_null_url_when_storage_is_unset(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)
    slot.store = None

    response = client.get(_admin_list_url(task.catalogue_service_id), headers=_admin_headers())

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert (item["id"], item["url"], item["byte_size"]) == (artifact["id"], None, len(HTML))


def test_admin_list_is_404_for_an_unknown_catalogue_row(client: TestClient[Litestar]) -> None:
    response = client.get(_admin_list_url(uuid.uuid4()), headers=_admin_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue service not found"


def test_machine_list_filters_by_kind_and_host_and_caps_the_limit(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    other = _kind_task(db_session, _catalogue(db_session, external_id="svc-2"), DiscoveryTaskKind.FETCH_URL)
    _stored(client, key, task)
    _stored(client, key, task, content=PNG, kind="screenshot", content_type="image/png")
    _stored(client, key, other, source_url="https://other.example.org/a?x=1")
    headers = {"X-API-Key": key}

    def listed(**params: str | int) -> list[dict[str, str]]:
        return client.get(f"{MACHINE}/artifacts", params=params, headers=headers).json()["items"]

    assert len(listed()) == 3
    assert [i["kind"] for i in listed(kind="screenshot")] == ["screenshot"]
    assert [i["source_url"] for i in listed(host="OTHER.example.org")] == ["https://other.example.org/a?x=1"]
    assert len(listed(host="example.gov")) == 2
    assert len(listed(limit=1)) == 1
    assert client.get(f"{MACHINE}/artifacts", params={"limit": 101}, headers=headers).status_code == 422


def test_artifact_read_routes_require_the_machine_key_or_an_admin(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)

    assert client.get(f"{MACHINE}/artifacts").status_code == 401
    assert client.get(f"{MACHINE}/artifacts/{artifact['id']}/content").status_code == 401
    assert client.get(_admin_list_url(task.catalogue_service_id)).status_code == 401
    assert client.get(_admin_list_url(task.catalogue_service_id), headers={"X-API-Key": key}).status_code == 401


def _enqueue_with(client: TestClient[Litestar], key: str, catalogue_id: uuid.UUID, artifact_id: object):
    body = {
        "catalogue_service_id": str(catalogue_id),
        "kind": "extract_page",
        "target_url": "https://example.gov/page",
        "artifact_id": str(artifact_id),
    }
    return client.post(MACHINE + "/tasks", json=body, headers={"X-API-Key": key})


def test_enqueue_accepts_an_artifact_of_the_same_catalogue_row_and_stores_it(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)

    response = _enqueue_with(client, key, task.catalogue_service_id, artifact["id"])

    assert response.status_code == 201
    created = db_session.get(DiscoveryTask, uuid.UUID(response.json()["id"]))
    assert created is not None and str(created.artifact_id) == artifact["id"]


def test_enqueue_with_an_artifact_from_another_catalogue_row_is_rejected(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    other = _catalogue(db_session, external_id="svc-other")
    artifact = _stored(client, key, task)

    mismatched = _enqueue_with(client, key, other.id, artifact["id"])
    unknown = _enqueue_with(client, key, other.id, uuid.uuid4())

    assert (mismatched.status_code, unknown.status_code) == (422, 404)
    assert (
        db_session.scalar(
            select(func.count()).select_from(DiscoveryTask).where(DiscoveryTask.catalogue_service_id == other.id)
        )
        == 0
    )
