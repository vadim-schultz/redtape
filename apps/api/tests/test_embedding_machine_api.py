"""HTTP behavior of the embedding machine routes (chapter 5)."""

from __future__ import annotations

import json
import uuid

import app.features.discovery.db_headroom as headroom_module
import pytest
from app.features.discovery.db_headroom import DatabaseHeadroom
from app.models.search import EMBEDDING_DIM, CandidateEmbedding, WorkTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from embedding_support import MODEL, current_hash, queued, unit_vector
from test_discovery_machine_api import _issue_key

BASE = "/api/v1/discovery/machine/embeddings"
ROUTES = [("POST", "claim"), ("POST", "complete"), ("POST", "fail"), ("POST", "release"), ("GET", "summary")]


def _headers(db_session: Session) -> dict[str, str]:
    return {"X-API-Key": _issue_key(db_session)}


def _claim_by_http(client: TestClient[Litestar], headers: dict[str, str]) -> list[dict[str, object]]:
    response = client.post(f"{BASE}/claim", json={"limit": 5, "model": MODEL}, headers=headers)
    assert response.status_code == 200
    return list(response.json()["items"])


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_a_missing_or_wrong_api_key_is_refused(
    client: TestClient[Litestar], db_session: Session, method: str, route: str
) -> None:
    body = {} if method == "POST" else None
    _headers(db_session)

    missing = client.request(method, f"{BASE}/{route}", json=body)
    wrong = client.request(method, f"{BASE}/{route}", json=body, headers={"X-API-Key": "not-a-key"})

    assert (missing.status_code, wrong.status_code) == (401, 401)


def test_claim_returns_the_leased_tasks_with_their_text(client: TestClient[Litestar], db_session: Session) -> None:
    candidate, task = queued(db_session)

    (item,) = _claim_by_http(client, _headers(db_session))

    assert item["task_id"] == str(task.id)
    assert item["candidate_id"] == str(candidate.id)
    assert (item["locale"], item["text"], item["text_hash"]) == (
        "de",
        "Kindergeldantrag",
        current_hash(db_session, task),
    )
    assert item["lease_expires_at"]


@pytest.mark.parametrize("limit", [0, 51])
def test_claim_refuses_a_limit_outside_one_to_fifty(
    client: TestClient[Litestar], db_session: Session, limit: int
) -> None:
    queued(db_session)

    response = client.post(f"{BASE}/claim", json={"limit": limit, "model": MODEL}, headers=_headers(db_session))

    assert response.status_code == 422


def test_complete_stores_the_vector_and_reports_each_item(client: TestClient[Litestar], db_session: Session) -> None:
    (candidate, task), (_, bad) = queued(db_session, "Gut"), queued(db_session, "Schlecht")
    headers = _headers(db_session)
    _claim_by_http(client, headers)
    items = [
        {"task_id": str(task.id), "text_hash": current_hash(db_session, task), "model": MODEL, "vector": unit_vector()},
        {"task_id": str(bad.id), "text_hash": current_hash(db_session, bad), "model": MODEL, "vector": [1.0]},
    ]

    response = client.post(f"{BASE}/complete", json={"items": items}, headers=headers)

    assert response.status_code == 200
    assert [(r["task_id"], r["outcome"]) for r in response.json()["items"]] == [
        (str(task.id), "stored"),
        (str(bad.id), "rejected"),
    ]
    assert [row.candidate_id for row in db_session.scalars(select(CandidateEmbedding))] == [candidate.id]


def test_complete_accepts_a_full_batch_of_fifty_vectors_and_refuses_an_oversize_body(
    client: TestClient[Litestar], db_session: Session
) -> None:
    headers = _headers(db_session)
    vector = [0.123456789] * EMBEDDING_DIM
    full = {"items": [{"task_id": str(uuid.uuid4()), "text_hash": "h", "model": MODEL, "vector": vector}] * 50}
    oversize = {"items": [], "padding": "x" * 3_000_000}

    accepted = client.post(f"{BASE}/complete", json=full, headers=headers)
    refused = client.post(
        f"{BASE}/complete", content=json.dumps(oversize), headers=headers | {"Content-Type": "application/json"}
    )

    assert accepted.status_code == 200
    assert refused.status_code == 413


def test_complete_refuses_more_than_fifty_items(client: TestClient[Litestar], db_session: Session) -> None:
    item = {"task_id": str(uuid.uuid4()), "text_hash": "h", "model": MODEL, "vector": [0.0]}

    response = client.post(f"{BASE}/complete", json={"items": [item] * 51}, headers=_headers(db_session))

    assert response.status_code == 422


def test_fail_settles_a_claimed_task_and_refuses_one_that_is_not_claimed(
    client: TestClient[Litestar], db_session: Session
) -> None:
    queued(db_session)
    headers = _headers(db_session)
    (item,) = _claim_by_http(client, headers)

    failed = client.post(
        f"{BASE}/fail", json={"task_id": item["task_id"], "error": "boom", "retryable": True}, headers=headers
    )
    refused = client.post(f"{BASE}/fail", json={"task_id": str(uuid.uuid4()), "error": "x"}, headers=headers)

    assert failed.status_code == 200
    assert failed.json() == {"task_id": item["task_id"], "status": "pending", "last_error": "boom"}
    assert refused.status_code == 409


def test_release_returns_claimed_tasks_without_consuming_an_attempt(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _, task = queued(db_session)
    headers = _headers(db_session)
    (item,) = _claim_by_http(client, headers)
    task_id = item["task_id"]

    response = client.post(f"{BASE}/release", json={"task_ids": [task_id, str(uuid.uuid4())]}, headers=headers)

    assert response.status_code == 200
    assert response.json()["released"] == [task_id]
    assert len(response.json()["skipped"]) == 1
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)


def test_summary_reports_the_ready_work_for_the_workflows_early_exit(
    client: TestClient[Litestar], db_session: Session
) -> None:
    headers = _headers(db_session)
    empty = client.get(f"{BASE}/summary", headers=headers)
    queued(db_session)
    queued(db_session, "Zweiter Antrag")

    busy = client.get(f"{BASE}/summary", headers=headers)

    assert empty.json()["pending_ready"] == 0
    body = busy.json()
    assert body.pop("oldest_pending_age_seconds") >= 0
    assert body == {
        "pending_ready": 2,
        "claimed": 0,
        "failed": 0,
        "stale_candidates": 2,
        "completed_24h": 0,
        "failed_24h": 0,
    }


@pytest.fixture
def full_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the route guard at a headroom whose database is above its soft limit."""
    monkeypatch.setattr(headroom_module, "db_headroom", DatabaseHeadroom(read_size=lambda: 2, limit=lambda: 1))


def test_claim_and_complete_answer_507_at_the_database_soft_limit_but_fail_release_and_summary_still_work(
    client: TestClient[Litestar], db_session: Session, full_database: None
) -> None:
    queued(db_session)
    headers = _headers(db_session)
    item = {"task_id": str(uuid.uuid4()), "text_hash": "h", "model": MODEL, "vector": [0.0]}

    claim = client.post(f"{BASE}/claim", json={"limit": 1, "model": MODEL}, headers=headers)
    complete = client.post(f"{BASE}/complete", json={"items": [item]}, headers=headers)
    fail = client.post(f"{BASE}/fail", json={"task_id": str(uuid.uuid4()), "error": "x"}, headers=headers)
    release = client.post(f"{BASE}/release", json={"task_ids": [str(uuid.uuid4())]}, headers=headers)
    summary = client.get(f"{BASE}/summary", headers=headers)

    assert [claim.status_code, complete.status_code] == [507, 507]
    assert claim.json()["detail"] == "database_soft_limit"
    assert [fail.status_code, release.status_code, summary.status_code] == [409, 200, 200]


def test_claim_below_the_soft_limit_is_not_refused(client: TestClient[Litestar], db_session: Session) -> None:
    queued(db_session)

    response = client.post(f"{BASE}/claim", json={"limit": 1, "model": MODEL}, headers=_headers(db_session))

    assert response.status_code == 200
    assert response.json()["items"]
