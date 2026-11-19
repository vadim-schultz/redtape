"""HTTP behavior of the artifact upload, read and status routes (chapter 14)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import app.features.discovery.dependencies as discovery_dependencies
import pytest
from app.config import settings
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind, DiscoveryTask, DiscoveryTaskKind
from app.shared.object_store import InMemoryObjectStore, MeteredObjectStore, ObjectStore, ObjectStoreMeter, noop_meter
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _admin_headers, _catalogue, _kind_task
from test_discovery_candidates_admin_api import _artifact, _auth, _candidate, _mention
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
    """Put the slot's store under the ledger meter the discovery routes pass to ``get_object_store``."""
    holder = StoreSlot()

    def metered_slot_store(meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
        return None if holder.store is None else MeteredObjectStore(holder.store, meter)

    monkeypatch.setattr(discovery_dependencies, "get_object_store", metered_slot_store)
    return holder


@pytest.fixture
def client(slot: StoreSlot, client: TestClient[Litestar]) -> TestClient[Litestar]:  # noqa: F811
    """The shared admin and machine test client, built after the store override is in place."""
    return client


def _used(db_session: Session, resource: BudgetResource) -> float:
    """How much of ``resource`` the ledger has counted in the current period."""
    return float(BudgetService(DiscoveryRepository(db_session)).status(resource, datetime.now(UTC)).used)


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


def _claim_extract(client: TestClient[Litestar], key: str) -> list[dict[str, object]]:
    response = client.post(
        MACHINE + "/tasks/claim", json={"limit": 5, "kinds": ["extract_page"]}, headers={"X-API-Key": key}
    )
    return response.json()["items"]


def test_claim_shows_the_artifact_and_input_key_an_enqueued_task_carries(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    artifact = _stored(client, key, task)
    body = {
        "catalogue_service_id": str(task.catalogue_service_id),
        "kind": "extract_page",
        "target_url": "https://example.gov/page",
        "artifact_id": artifact["id"],
        "input_key": "verwaltung-bund@1",
    }
    assert client.post(MACHINE + "/tasks", json=body, headers={"X-API-Key": key}).status_code == 201

    items = _claim_extract(client, key)

    assert [(item["artifact_id"], item["input_key"]) for item in items] == [(artifact["id"], "verwaltung-bund@1")]


def test_claim_shows_nulls_for_a_task_enqueued_without_an_artifact_or_input_key(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    body = {
        "catalogue_service_id": str(task.catalogue_service_id),
        "kind": "extract_page",
        "target_url": "https://example.gov/page",
    }
    assert client.post(MACHINE + "/tasks", json=body, headers={"X-API-Key": key}).status_code == 201

    items = _claim_extract(client, key)

    assert [(item["artifact_id"], item["input_key"]) for item in items] == [(None, None)]


STATUS_URL = f"{MACHINE}/artifacts/status"


def test_artifacts_status_reports_a_store_and_the_bytes_against_the_cap(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    monkeypatch.setattr(settings, "object_store_max_bytes", 1000)
    _stored(client, key, task)

    response = client.get(STATUS_URL, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json() == {"storage_enabled": True, "bytes_used": len(HTML), "bytes_cap": 1000}


def test_artifacts_status_is_disabled_without_a_store_or_when_the_cap_is_reached(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    monkeypatch.setattr(settings, "object_store_max_bytes", len(HTML))
    _stored(client, key, task)

    full = client.get(STATUS_URL, headers={"X-API-Key": key}).json()
    slot.store = None
    unset = client.get(STATUS_URL, headers={"X-API-Key": key}).json()

    assert (full["storage_enabled"], full["bytes_used"], full["bytes_cap"]) == (False, len(HTML), len(HTML))
    assert unset["storage_enabled"] is False


def test_artifacts_status_requires_the_machine_key(client: TestClient[Litestar]) -> None:
    assert client.get(STATUS_URL).status_code == 401


def test_a_denied_class_a_reservation_answers_503_and_writes_no_row_or_object(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    monkeypatch.setattr(settings, "budget_r2_class_a_monthly", 0)

    response = _upload(client, key, task.id)

    assert response.status_code == 503
    assert _artifacts(db_session, task.catalogue_service_id) == []
    assert slot.memory.stored_keys() == []
    assert _used(db_session, BudgetResource.R2_CLASS_A) == 0


def test_an_upload_within_the_budget_counts_one_class_a_operation(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)

    assert _upload(client, key, task.id).status_code == 201

    assert _used(db_session, BudgetResource.R2_CLASS_A) == 1


def test_the_admin_artifact_list_counts_one_class_b_operation_per_presigned_url(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    _stored(client, key, task)
    _stored(client, key, task, content=PNG, kind="screenshot", content_type="image/png")

    response = client.get(_admin_list_url(task.catalogue_service_id), headers=_admin_headers())

    assert len(response.json()["items"]) == 2
    assert _used(db_session, BudgetResource.R2_CLASS_B) == 2


def test_the_admin_artifact_list_answers_503_without_minting_urls_when_class_b_is_exhausted(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    _stored(client, key, task)
    monkeypatch.setattr(settings, "budget_r2_class_b_monthly", 0)

    response = client.get(_admin_list_url(task.catalogue_service_id), headers=_admin_headers())

    assert response.status_code == 503


def test_the_admin_artifact_list_counts_nothing_when_storage_is_unset(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    key, task = _issue_key(db_session), _task(db_session)
    _stored(client, key, task)
    slot.store = None

    client.get(_admin_list_url(task.catalogue_service_id), headers=_admin_headers())

    assert _used(db_session, BudgetResource.R2_CLASS_B) == 0


def _candidate_artifacts_url(candidate_id: uuid.UUID) -> str:
    return f"/api/v1/discovery/admin/candidates/{candidate_id}/artifacts"


def test_candidate_artifacts_returns_referenced_artifacts_and_latest_procedure_screenshots_without_duplicates(
    client: TestClient[Litestar], db_session: Session
) -> None:
    first, second = _catalogue(db_session), _catalogue(db_session, external_id="svc-2")
    candidate = _candidate(db_session, first, key="personalausweis")
    snapshot = _artifact(db_session, first)
    old_shot = _artifact(db_session, first, DiscoveryArtifactKind.SCREENSHOT, fetched_at=FETCHED_AT)
    new_shot = _artifact(db_session, first, DiscoveryArtifactKind.SCREENSHOT, fetched_at=FETCHED_AT + timedelta(days=1))
    other_shot = _artifact(db_session, second, DiscoveryArtifactKind.SCREENSHOT)
    _artifact(db_session, second)
    _mention(db_session, candidate, first, "a", artifact=snapshot)
    _mention(db_session, candidate, first, "b", artifact=snapshot)
    _mention(db_session, candidate, second, "c")

    body = client.get(_candidate_artifacts_url(candidate.id), headers=_admin_headers()).json()

    ids = [item["id"] for item in body["items"]]
    assert sorted(ids) == sorted(str(row.id) for row in (snapshot, new_shot, other_shot))
    assert str(old_shot.id) not in ids
    assert body["total"] == 3
    assert all(item["url"].startswith("memory://") for item in body["items"])


def test_candidate_artifacts_pages_and_counts_one_class_b_operation_per_minted_url(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    _mention(db_session, candidate, catalogue, "a", artifact=_artifact(db_session, catalogue))
    _artifact(db_session, catalogue, DiscoveryArtifactKind.SCREENSHOT)

    body = client.get(_candidate_artifacts_url(candidate.id), params={"limit": 1}, headers=_admin_headers()).json()

    assert (body["total"], len(body["items"]), body["limit"]) == (2, 1, 1)
    assert _used(db_session, BudgetResource.R2_CLASS_B) == 1


def test_candidate_artifacts_answers_503_without_minting_urls_when_class_b_is_exhausted(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    _mention(db_session, candidate, catalogue, "a", artifact=_artifact(db_session, catalogue))
    monkeypatch.setattr(settings, "budget_r2_class_b_monthly", 0)

    response = client.get(_candidate_artifacts_url(candidate.id), headers=_admin_headers())

    assert response.status_code == 503


def test_candidate_artifacts_degrades_to_null_urls_when_storage_is_unset(
    client: TestClient[Litestar], slot: StoreSlot, db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    snapshot = _artifact(db_session, catalogue)
    _mention(db_session, candidate, catalogue, "a", artifact=snapshot)
    slot.store = None

    response = client.get(_candidate_artifacts_url(candidate.id), headers=_admin_headers())

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert (item["id"], item["url"]) == (str(snapshot.id), None)
    assert _used(db_session, BudgetResource.R2_CLASS_B) == 0


def test_candidate_artifacts_rejects_non_admins_and_returns_404_for_an_unknown_candidate(
    client: TestClient[Litestar], db_session: Session
) -> None:
    candidate = _candidate(db_session, _catalogue(db_session), key="personalausweis")

    forbidden = client.get(_candidate_artifacts_url(candidate.id), headers=_auth("stranger@example.com"))
    anonymous = client.get(_candidate_artifacts_url(candidate.id))
    unknown = client.get(_candidate_artifacts_url(uuid.uuid4()), headers=_admin_headers())

    assert (forbidden.status_code, anonymous.status_code, unknown.status_code) == (403, 401, 404)
    assert unknown.json()["detail"] == "Document candidate not found"


MISSING_SCREENSHOT = f"{MACHINE}/artifacts/missing-screenshot"


def test_missing_screenshot_lists_each_rendered_page_without_a_screenshot(
    client: TestClient[Litestar], db_session: Session
) -> None:
    """missing-screenshot · a rendered page with no screenshot is listed; a page with one, or never rendered, is not."""
    key = _issue_key(db_session)
    bare, shot, unrendered = _task(db_session, "svc-bare"), _task(db_session, "svc-shot"), _task(db_session, "svc-none")
    _stored(client, key, bare, source_url="https://example.gov/bare")
    _stored(client, key, shot, source_url="https://example.gov/shot")
    _stored(client, key, shot, content=PNG, kind="screenshot", content_type="image/png")
    _stored(client, key, unrendered, content=PNG, kind="screenshot", content_type="image/png")

    items = client.get(MISSING_SCREENSHOT, headers={"X-API-Key": key}).json()["items"]

    assert [(item["catalogue_service_id"], item["source_url"]) for item in items] == [
        (str(bare.catalogue_service_id), "https://example.gov/bare")
    ]


def test_missing_screenshot_answers_the_newest_html_snapshot_of_each_page_once(
    client: TestClient[Litestar], db_session: Session
) -> None:
    """missing-screenshot · a page with two snapshots is listed once, by its newest one."""
    key, task = _issue_key(db_session), _task(db_session)
    _snapshot(client, key, task.id, 1)
    newest = _snapshot(client, key, task.id, 3)

    items = client.get(MISSING_SCREENSHOT, headers={"X-API-Key": key}).json()["items"]

    assert [item["storage_key"] for item in items] == [newest]


def test_missing_screenshot_filters_by_catalogue_and_caps_the_limit(
    client: TestClient[Litestar], db_session: Session
) -> None:
    """missing-screenshot · catalogue_service_id keeps one page, limit keeps the page size, and 101 is refused."""
    key = _issue_key(db_session)
    first, second = _task(db_session, "svc-a"), _task(db_session, "svc-b")
    _stored(client, key, first, source_url="https://example.gov/a")
    _stored(client, key, second, source_url="https://example.gov/b")
    headers = {"X-API-Key": key}

    only_second = client.get(
        MISSING_SCREENSHOT, params={"catalogue_service_id": str(second.catalogue_service_id)}, headers=headers
    ).json()["items"]

    assert [item["source_url"] for item in only_second] == ["https://example.gov/b"]
    assert len(client.get(MISSING_SCREENSHOT, params={"limit": 1}, headers=headers).json()["items"]) == 1
    assert client.get(MISSING_SCREENSHOT, params={"limit": 101}, headers=headers).status_code == 422


def test_missing_screenshot_requires_the_machine_key(client: TestClient[Litestar]) -> None:
    """missing-screenshot · without the machine key the route answers 401 and lists nothing."""
    assert client.get(MISSING_SCREENSHOT).status_code == 401
