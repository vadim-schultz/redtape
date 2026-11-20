"""HTTP behavior of discovery machine routes (chapter 3)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.main import create_app
from app.models.discovery import (
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_task_superseded import _artifact, _completed

BATCH_URL = "/api/v1/discovery/machine/catalogue/batch"
CLAIM_URL = "/api/v1/discovery/machine/tasks/claim"
SUMMARY_URL = "/api/v1/discovery/machine/tasks/summary"
ENQUEUE_URL = "/api/v1/discovery/machine/tasks"


def _fail_url(task_id: uuid.UUID) -> str:
    return f"{ENQUEUE_URL}/{task_id}/fail"


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _issue_key(db_session: Session) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-ingest")
    service.verify(key)
    db_session.flush()
    return key


def _batch_item(country: Jurisdiction, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "source": "govdata",
        "external_id": "svc-42",
        "jurisdiction_id": str(country.id),
        "title_i18n": {"de": "Leistung"},
        "portal_url": "https://example.gov/service",
        "raw_payload": {"id": "svc-42"},
    }
    body.update(overrides)
    return body


def test_post_catalogue_batch_upserts_row_and_creates_pending_fetch_task_when_portal_url_set(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country)]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["external_id"] == "svc-42"
    assert body["items"][0]["task_id"] is not None

    task_id = uuid.UUID(body["items"][0]["task_id"])
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.kind == DiscoveryTaskKind.FETCH_URL
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.target_url == "https://example.gov/service"

    events = list(
        db_session.scalars(
            select(DiscoveryEvent).where(DiscoveryEvent.event_type == DiscoveryEventType.CATALOGUE_UPSERTED)
        )
    )
    assert len(events) == 1
    enqueued = list(
        db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.event_type == DiscoveryEventType.TASK_ENQUEUED))
    )
    assert len(enqueued) == 1


def test_post_catalogue_batch_returns_401_without_api_key(
    client: TestClient[Litestar],
    country: Jurisdiction,
) -> None:
    response = client.post(BATCH_URL, json={"items": [_batch_item(country)]})

    assert response.status_code == 401


def test_post_catalogue_batch_returns_422_for_unknown_jurisdiction_id(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    unknown_jurisdiction_id = uuid.uuid4()
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, jurisdiction_id=str(unknown_jurisdiction_id))]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "jurisdiction" in detail.lower()


def test_post_catalogue_batch_returns_422_for_missing_external_id(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    item = _batch_item(country)
    del item["external_id"]
    response = client.post(BATCH_URL, json={"items": [item]}, headers={"X-API-Key": key})

    assert response.status_code == 422


def test_post_tasks_claim_assigns_pending_tasks_to_the_caller_key(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="claim-me")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert claim.status_code == 200
    items = claim.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(task_id)
    assert items[0]["status"] == "claimed"
    assert items[0]["lease_expires_at"] is not None

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.status == DiscoveryTaskStatus.CLAIMED
    assert task.claimed_by_api_key_id is not None


def test_post_tasks_claim_returns_empty_list_when_queue_drained(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    response = client.post(CLAIM_URL, json={"limit": 5}, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json()["items"] == []


def _seed_pending(db_session: Session, kind: DiscoveryTaskKind) -> DiscoveryTask:
    catalogue = _catalogue(db_session, external_id=f"seed-{kind.value}")
    target = TaskTarget(catalogue_service_id=catalogue.id, kind=kind, target_url=f"https://example.gov/{kind.value}")
    return DiscoveryRepository(db_session).insert_task(target)


def test_post_tasks_claim_with_kinds_leases_only_those_kinds(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    extract = _seed_pending(db_session, DiscoveryTaskKind.EXTRACT_PAGE)

    claim = client.post(CLAIM_URL, json={"limit": 5, "kinds": ["extract_page"]}, headers={"X-API-Key": key})

    assert claim.status_code == 200
    assert [item["id"] for item in claim.json()["items"]] == [str(extract.id)]


def test_post_tasks_claim_without_kinds_never_leases_new_kinds(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    extract = _seed_pending(db_session, DiscoveryTaskKind.EXTRACT_PAGE)

    claim = client.post(CLAIM_URL, json={"limit": 5}, headers={"X-API-Key": key})

    assert claim.status_code == 200
    assert claim.json()["items"] == []
    assert extract.status == DiscoveryTaskStatus.PENDING


@pytest.mark.parametrize("kinds", [[], ["no_such_kind"]])
def test_post_tasks_claim_rejects_empty_or_unknown_kinds_without_leasing(
    client: TestClient[Litestar],
    db_session: Session,
    kinds: list[str],
) -> None:
    key = _issue_key(db_session)
    fetch = _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)

    claim = client.post(CLAIM_URL, json={"limit": 5, "kinds": kinds}, headers={"X-API-Key": key})

    assert claim.status_code == 422
    assert fetch.status == DiscoveryTaskStatus.PENDING


def test_post_tasks_claim_reclaims_expired_claimed_task(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="lease-expired")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    first_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})
    assert first_claim.status_code == 200
    assert len(first_claim.json()["items"]) == 1

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    task.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()

    second_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert second_claim.status_code == 200
    items = second_claim.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(task_id)
    assert items[0]["status"] == "claimed"

    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.CLAIMED
    assert task.claimed_by_api_key_id is not None
    assert task.lease_expires_at is not None
    assert task.lease_expires_at > datetime.now(UTC)


def test_post_tasks_claim_does_not_reclaim_task_with_future_lease(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="lease-active")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    first_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})
    assert first_claim.status_code == 200
    assert len(first_claim.json()["items"]) == 1

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    task.lease_expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.flush()

    second_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert second_claim.status_code == 200
    assert second_claim.json()["items"] == []

    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.CLAIMED


def _claimed_task(client: TestClient[Litestar], db_session: Session, key: str) -> uuid.UUID:
    _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})
    return uuid.UUID(claim.json()["items"][0]["id"])


def test_post_task_fail_with_retryable_returns_the_task_to_pending(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    response = client.post(_fail_url(task_id), json={"error": "timeout", "retryable": True}, headers={"X-API-Key": key})

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.not_before is not None


def test_post_task_fail_without_retryable_stays_failed(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    response = client.post(_fail_url(task_id), json={"error": "http 404"}, headers={"X-API-Key": key})

    assert response.json()["status"] == "failed"
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.not_before is None


def test_post_tasks_fetches_appends_fetch_log_and_leaves_task_claimed(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="fetch-me")]},
        headers={"X-API-Key": key},
    )
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])
    client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    fetches_url = f"/api/v1/discovery/machine/tasks/{task_id}/fetches"
    response = client.post(
        fetches_url,
        json={"http_status": 200, "content_type": "text/html", "byte_length": 1024},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["task_status"] == "claimed"

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.status == DiscoveryTaskStatus.CLAIMED

    logs = list(db_session.scalars(select(DiscoveryFetchLog).where(DiscoveryFetchLog.discovery_task_id == task_id)))
    assert len(logs) == 1
    assert logs[0].http_status == 200


def _enqueue_body(catalogue_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "catalogue_service_id": str(catalogue_id),
        "kind": "extract_page",
        "target_url": "https://example.gov/page",
    }
    body.update(overrides)
    return body


def _tasks_for(db_session: Session, catalogue_id: uuid.UUID) -> list[DiscoveryTask]:
    stmt = select(DiscoveryTask).where(DiscoveryTask.catalogue_service_id == catalogue_id)
    return list(db_session.scalars(stmt).all())


def test_post_tasks_enqueue_creates_a_pending_task_and_records_an_event(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = client.post(
        ENQUEUE_URL, json=_enqueue_body(catalogue.id, input_key="html@1", priority=5), headers={"X-API-Key": key}
    )

    assert response.status_code == 201
    assert response.json()["created"] is True
    task = db_session.get(DiscoveryTask, uuid.UUID(response.json()["id"]))
    assert task is not None
    assert (task.kind, task.status, task.priority, task.input_key) == (
        DiscoveryTaskKind.EXTRACT_PAGE,
        DiscoveryTaskStatus.PENDING,
        5,
        "html@1",
    )
    events = db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.discovery_task_id == task.id)).all()
    assert [event.event_type for event in events] == [DiscoveryEventType.TASK_ENQUEUED]


def test_post_tasks_enqueue_is_idempotent_for_the_same_target_and_input_key(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    body = _enqueue_body(catalogue.id, input_key="html@1")

    first = client.post(ENQUEUE_URL, json=body, headers={"X-API-Key": key})
    second = client.post(ENQUEUE_URL, json=body, headers={"X-API-Key": key})

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == {"id": first.json()["id"], "created": False}
    assert len(_tasks_for(db_session, catalogue.id)) == 1


def test_post_tasks_enqueue_distinguishes_input_keys(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    responses = [
        client.post(ENQUEUE_URL, json=_enqueue_body(catalogue.id, **extra), headers={"X-API-Key": key})
        for extra in ({}, {"input_key": "html@1"}, {"input_key": "html@2"})
    ]

    assert [r.status_code for r in responses] == [201, 201, 201]
    assert len({r.json()["id"] for r in responses}) == 3
    assert len(_tasks_for(db_session, catalogue.id)) == 3


def test_post_tasks_enqueue_returns_404_for_an_unknown_catalogue_row(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)

    response = client.post(ENQUEUE_URL, json=_enqueue_body(uuid.uuid4()), headers={"X-API-Key": key})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [{"kind": "no_such_kind"}, {"target_url": "https://example.gov/" + "x" * 500}, {"input_key": "k" * 129}],
)
def test_post_tasks_enqueue_returns_422_for_invalid_bodies_and_creates_nothing(
    client: TestClient[Litestar],
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = client.post(ENQUEUE_URL, json=_enqueue_body(catalogue.id, **overrides), headers={"X-API-Key": key})

    assert response.status_code == 422
    assert _tasks_for(db_session, catalogue.id) == []


def _complete_url(task_id: uuid.UUID) -> str:
    return f"{ENQUEUE_URL}/{task_id}/complete"


def _release_url(task_id: uuid.UUID) -> str:
    return f"{ENQUEUE_URL}/{task_id}/release"


def test_post_task_complete_stores_an_optional_note(client: TestClient[Litestar], db_session: Session) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    response = client.post(_complete_url(task_id), json={"note": "no_mentions"}, headers={"X-API-Key": key})

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.result_note == "no_mentions"


def test_post_task_complete_without_a_body_still_works_and_a_long_note_is_rejected(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    too_long = client.post(_complete_url(task_id), json={"note": "x" * 201}, headers={"X-API-Key": key})
    bare = client.post(_complete_url(task_id), headers={"X-API-Key": key})

    assert too_long.status_code == 422
    assert bare.status_code == 201 and bare.json()["status"] == "completed"
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.result_note is None


def test_post_task_release_returns_the_task_to_pending_without_consuming_an_attempt(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)
    not_before = datetime.now(UTC) + timedelta(hours=1)

    response = client.post(
        _release_url(task_id),
        json={"reason": "browser_quota", "not_before": not_before.isoformat()},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(task_id), "status": "pending", "last_error": "browser_quota"}
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert (task.attempt_count, task.not_before, task.claimed_by_api_key_id) == (0, not_before, None)


def test_post_task_release_rejects_a_task_that_is_not_claimed_and_an_unknown_task(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)
    pending = _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    body = {"reason": "storage_unavailable"}

    not_claimed = client.post(_release_url(pending.id), json=body, headers={"X-API-Key": key})
    unknown = client.post(_release_url(uuid.uuid4()), json=body, headers={"X-API-Key": key})
    missing_reason = client.post(_release_url(pending.id), json={}, headers={"X-API-Key": key})

    assert (not_claimed.status_code, unknown.status_code, missing_reason.status_code) == (409, 404, 422)
    assert pending.status == DiscoveryTaskStatus.PENDING


REQUEUE_URL = "/api/v1/discovery/machine/tasks/requeue-transient"


def _task_row(db_session: Session, task_id: uuid.UUID) -> DiscoveryTask:
    row = db_session.get(DiscoveryTask, task_id)
    assert row is not None
    return row


def _failed_task(db_session: Session, *, failure_class: str, age: timedelta) -> DiscoveryTask:
    task = _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    task.status = DiscoveryTaskStatus.FAILED
    task.failure_class = failure_class
    task.attempt_count = 3
    task.updated_at = datetime.now(UTC) - age
    db_session.flush()
    return task


def test_post_requeue_transient_returns_the_count_of_tasks_put_back(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    due = _failed_task(db_session, failure_class="transient", age=timedelta(hours=25))

    response = client.post(REQUEUE_URL, json={"limit": 10}, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json() == {"requeued": 1}
    assert _task_row(db_session, due.id).status is DiscoveryTaskStatus.PENDING


@pytest.mark.parametrize("limit", [0, 201])
def test_post_requeue_transient_rejects_a_limit_outside_one_to_200(
    client: TestClient[Litestar],
    db_session: Session,
    limit: int,
) -> None:
    key = _issue_key(db_session)
    failed = _failed_task(db_session, failure_class="transient", age=timedelta(hours=25))

    response = client.post(REQUEUE_URL, json={"limit": limit}, headers={"X-API-Key": key})

    assert response.status_code == 422
    assert _task_row(db_session, failed.id).status is DiscoveryTaskStatus.FAILED


SUPERSEDED_URL = "/api/v1/discovery/machine/tasks/requeue-superseded"


def test_post_requeue_superseded_repends_an_older_extraction_and_reports_both_counts(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    """machine API · happy: the route answers matched and requeued, and the older extraction is pending under the new key."""
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session, external_id="superseded-route")
    artifact = _artifact(db_session, catalogue)
    old = _completed(
        db_session, catalogue, url="https://example.gov/route", input_key="llm:old00005", artifact=artifact
    )

    response = client.post(
        SUPERSEDED_URL,
        json={"kind": "llm_extract", "input_key": "llm:cur00001", "limit": 10},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    assert response.json() == {"matched": 1, "requeued": 1}
    assert _task_row(db_session, old.id).input_key == "llm:cur00001"


@pytest.mark.parametrize(
    "body",
    [{"kind": "llm_extract", "input_key": "llm:cur00001", "limit": 0}, {"kind": "llm_extract", "limit": 10}],
)
def test_post_requeue_superseded_rejects_a_limit_below_one_or_a_missing_key(
    client: TestClient[Litestar],
    db_session: Session,
    body: dict[str, object],
) -> None:
    """machine API · negative: a limit of 0 or a missing input_key is a validation error (422) and changes no row."""
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session, external_id="superseded-refused")
    artifact = _artifact(db_session, catalogue)
    old = _completed(
        db_session, catalogue, url="https://example.gov/refused", input_key="llm:old00005", artifact=artifact
    )

    response = client.post(SUPERSEDED_URL, json=body, headers={"X-API-Key": key})

    assert response.status_code == 422
    assert _task_row(db_session, old.id).status is DiscoveryTaskStatus.COMPLETED


def test_post_task_fail_stores_the_failure_class_the_worker_sends(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    response = client.post(
        _fail_url(task_id),
        json={"error": "robots.txt disallows", "failure_class": "robots"},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.failure_class == "robots"


def test_post_task_fail_rejects_an_unknown_failure_class_and_changes_nothing(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    task_id = _claimed_task(client, db_session, key)

    response = client.post(
        _fail_url(task_id), json={"error": "boom", "failure_class": "fatal"}, headers={"X-API-Key": key}
    )

    assert response.status_code == 422
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None and task.status is DiscoveryTaskStatus.CLAIMED
