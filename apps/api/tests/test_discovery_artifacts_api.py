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

from test_discovery_admin_api import _catalogue, _kind_task
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
