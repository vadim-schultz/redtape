"""HTTP behavior of the translation machine routes (chapter 14)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

import app.features.discovery.db_headroom as headroom_module
import app.features.discovery.dependencies as discovery_dependencies
import pytest
from app.features.discovery.db_headroom import DatabaseHeadroom
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation
from app.shared.object_store import InMemoryObjectStore, MeteredObjectStore, ObjectStore, ObjectStoreMeter, noop_meter
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as client  # noqa: F401
from translation_support import enqueuer, queued_task, task_rows, unit_candidate, unit_hash

BASE = "/api/v1/discovery/machine/translations"
ROUTES = [("POST", "claim"), ("POST", "complete"), ("POST", "fail"), ("POST", "release"), ("GET", "summary")]


class StoreSlot:
    """The store the test app resolves for its ``object_store`` dependency."""

    def __init__(self) -> None:
        self.store: ObjectStore | None = InMemoryObjectStore()


@pytest.fixture
def slot(monkeypatch: pytest.MonkeyPatch) -> StoreSlot:
    """Put the slot's store under the ledger meter the discovery routes pass to ``get_object_store``."""
    holder = StoreSlot()

    def metered(meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
        return None if holder.store is None else MeteredObjectStore(holder.store, meter)

    monkeypatch.setattr(discovery_dependencies, "get_object_store", metered)
    return holder


@pytest.fixture
def api(slot: StoreSlot, client: TestClient[Litestar]) -> Iterator[TestClient[Litestar]]:  # noqa: F811
    """The shared machine test client, built after the store override is in place."""
    yield client


def _headers(db_session: Session) -> dict[str, str]:
    return {"X-API-Key": _issue_key(db_session)}


def _claim(client: TestClient[Litestar], headers: dict[str, str], limit: int = 5) -> list[dict[str, object]]:
    response = client.post(f"{BASE}/claim", json={"limit": limit}, headers=headers)
    assert response.status_code == 200
    return list(response.json()["items"])


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_a_missing_or_wrong_api_key_is_refused(
    api: TestClient[Litestar], db_session: Session, method: str, route: str
) -> None:
    body = {} if method == "POST" else None

    missing = api.request(method, f"{BASE}/{route}", json=body)
    wrong = api.request(method, f"{BASE}/{route}", json=body, headers={"X-API-Key": "not-a-key"})

    assert (missing.status_code, wrong.status_code) == (401, 401)


def test_claim_returns_the_leased_tasks_with_their_german_source(
    api: TestClient[Litestar], db_session: Session
) -> None:
    candidate, task = queued_task(db_session)

    (item,) = _claim(api, _headers(db_session))

    assert item["task_id"] == str(task.id)
    assert (item["candidate_id"], item["locale"], item["source_locale"]) == (str(candidate.id), "en", "de")
    assert (item["title"], item["description"]) == ("Kindergeldantrag", "Bitte Ausweis mitbringen")
    assert item["source_hash"] == unit_hash(db_session, candidate)
    assert item["lease_expires_at"]


@pytest.mark.parametrize("limit", [0, 51])
def test_claim_refuses_a_limit_outside_one_to_fifty(api: TestClient[Litestar], db_session: Session, limit: int) -> None:
    queued_task(db_session)

    response = api.post(f"{BASE}/claim", json={"limit": limit}, headers=_headers(db_session))

    assert response.status_code == 422


def test_complete_stores_the_text_and_reports_each_item(api: TestClient[Litestar], db_session: Session) -> None:
    _, good = queued_task(db_session, title="Gut")
    _, bad = queued_task(db_session, title="Schlecht")
    headers = _headers(db_session)
    served = {item["task_id"]: item for item in _claim(api, headers)}
    items = [
        {
            "task_id": str(task.id),
            "source_hash": served[str(task.id)]["source_hash"],
            "title": title,
            "description": "d",
            "engine": "llm",
            "model": "m",
        }
        for task, title in ((good, "Good"), (bad, ""))
    ]

    response = api.post(f"{BASE}/complete", json={"items": items}, headers=headers)

    assert response.status_code == 200
    assert [(r["task_id"], r["outcome"]) for r in response.json()["items"]] == [
        (str(good.id), "stored"),
        (str(bad.id), "rejected"),
    ]
    assert [row.candidate_id for row in db_session.scalars(select(CandidateTranslation))] == [good.candidate_id]


def test_complete_answers_unavailable_when_object_storage_is_not_configured(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    candidate, task = queued_task(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    slot.store = None
    item = {
        "task_id": str(task.id),
        "source_hash": served["source_hash"],
        "title": "t",
        "description": "d",
        "engine": "llm",
        "model": "m",
    }

    response = api.post(f"{BASE}/complete", json={"items": [item]}, headers=headers)

    assert response.status_code == 200
    assert [r["outcome"] for r in response.json()["items"]] == ["unavailable"]
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)
    assert candidate.id and db_session.scalars(select(CandidateTranslation)).all() == []


def test_complete_accepts_a_full_batch_and_refuses_an_oversize_body_or_too_many_items(
    api: TestClient[Litestar], db_session: Session
) -> None:
    headers = _headers(db_session)
    item = {
        "task_id": str(uuid.uuid4()),
        "source_hash": "h",
        "title": "t" * 300,
        "description": "d" * 4000,
        "engine": "llm",
        "model": "m",
    }
    oversize = {"items": [], "padding": "x" * 3_000_000}

    accepted = api.post(f"{BASE}/complete", json={"items": [item] * 50}, headers=headers)
    refused = api.post(
        f"{BASE}/complete", content=json.dumps(oversize), headers=headers | {"Content-Type": "application/json"}
    )
    too_many = api.post(f"{BASE}/complete", json={"items": [item] * 51}, headers=headers)

    assert (accepted.status_code, refused.status_code, too_many.status_code) == (200, 413, 422)


def test_fail_settles_a_claimed_task_and_refuses_one_that_is_not_claimed(
    api: TestClient[Litestar], db_session: Session
) -> None:
    queued_task(db_session)
    headers = _headers(db_session)
    (item,) = _claim(api, headers)

    failed = api.post(
        f"{BASE}/fail", json={"task_id": item["task_id"], "error": "boom", "retryable": True}, headers=headers
    )
    refused = api.post(f"{BASE}/fail", json={"task_id": str(uuid.uuid4()), "error": "x"}, headers=headers)

    assert failed.status_code == 200
    assert failed.json() == {"task_id": item["task_id"], "status": "pending", "last_error": "boom"}
    assert refused.status_code == 409


def test_release_returns_claimed_tasks_without_consuming_an_attempt(
    api: TestClient[Litestar], db_session: Session
) -> None:
    _, task = queued_task(db_session)
    headers = _headers(db_session)
    (item,) = _claim(api, headers)

    response = api.post(
        f"{BASE}/release", json={"task_ids": [item["task_id"], str(uuid.uuid4())], "reason": "budget"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["released"] == [item["task_id"]]
    assert len(response.json()["skipped"]) == 1
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)


def test_summary_reports_pending_ready_and_translated_counts_per_locale(
    api: TestClient[Litestar], db_session: Session
) -> None:
    headers = _headers(db_session)
    empty = api.get(f"{BASE}/summary", headers=headers).json()
    candidate = unit_candidate(db_session)
    enqueuer(db_session, ("en", "tr")).enqueue_many([candidate.id])
    done = task_rows(db_session)[0]
    done.status = WorkTaskStatus.COMPLETED
    from translation_support import stored_row

    stored_row(db_session, candidate, done.locale, unit_hash(db_session, candidate))

    busy = api.get(f"{BASE}/summary", headers=headers).json()

    zero = {"pending_ready": 0, "claimed": 0, "failed": 0, "stale": 0, "translated": 0}
    assert {entry["locale"]: entry for entry in empty["locales"]}["en"] == {"locale": "en", **zero}
    by_locale = {entry["locale"]: entry for entry in busy["locales"]}
    assert by_locale[done.locale]["translated"] == 1
    other = "tr" if done.locale == "en" else "en"
    assert (by_locale[other]["pending_ready"], by_locale[other]["translated"]) == (1, 0)
    assert by_locale["ru"] == {"locale": "ru", **zero}


def test_summary_counts_a_translation_with_an_open_task_for_a_newer_text_as_stale(
    api: TestClient[Litestar], db_session: Session
) -> None:
    from translation_support import stored_row

    candidate = unit_candidate(db_session)
    stored_row(db_session, candidate, "en", "old-hash")
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])

    summary = api.get(f"{BASE}/summary", headers=_headers(db_session)).json()

    en = {entry["locale"]: entry for entry in summary["locales"]}["en"]
    assert (en["stale"], en["translated"], en["pending_ready"]) == (1, 1, 1)


@pytest.fixture
def full_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the route guard at a headroom whose database is above its soft limit."""
    monkeypatch.setattr(headroom_module, "db_headroom", DatabaseHeadroom(read_size=lambda: 2, limit=lambda: 1))


def test_claim_and_complete_answer_507_at_the_database_soft_limit_but_fail_release_and_summary_still_work(
    api: TestClient[Litestar], db_session: Session, full_database: None
) -> None:
    queued_task(db_session)
    headers = _headers(db_session)
    item = {
        "task_id": str(uuid.uuid4()),
        "source_hash": "h",
        "title": "t",
        "description": "d",
        "engine": "llm",
        "model": "m",
    }

    claim = api.post(f"{BASE}/claim", json={"limit": 1}, headers=headers)
    complete = api.post(f"{BASE}/complete", json={"items": [item]}, headers=headers)
    fail = api.post(f"{BASE}/fail", json={"task_id": str(uuid.uuid4()), "error": "x"}, headers=headers)
    release = api.post(f"{BASE}/release", json={"task_ids": [str(uuid.uuid4())]}, headers=headers)
    summary = api.get(f"{BASE}/summary", headers=headers)

    assert [claim.status_code, complete.status_code] == [507, 507]
    assert claim.json()["detail"] == "database_soft_limit"
    assert [fail.status_code, release.status_code, summary.status_code] == [409, 200, 200]


def test_claim_below_the_soft_limit_is_not_refused(api: TestClient[Litestar], db_session: Session) -> None:
    queued_task(db_session)

    response = api.post(f"{BASE}/claim", json={"limit": 1}, headers=_headers(db_session))

    assert response.status_code == 200
    assert response.json()["items"]
