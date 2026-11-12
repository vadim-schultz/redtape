"""HTTP behaviour of the snapshot machine routes (chapter 08): claim by reference, complete by outcome, fail, release, summary."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Final

import pytest
from app.features.translation.task_repository import TaskRepository
from app.models.search import WorkTaskStatus
from app.shared.object_store import InMemoryObjectStore
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from embedding_support import NOW
from snapshot_machine_support import (
    HASH_NEW,
    HASH_STORED,
    SHA_A,
    SHA_B,
    SHA_OLD,
    SOURCE_URL,
    add_snapshot,
    index_row,
    queue_page,
    skipped_row,
    stored_row,
    task_in_state,
    task_rows,
)
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as client  # noqa: F401
from test_snapshot_models import catalogue_row
from test_translation_machine_api import StoreSlot
from test_translation_machine_api import slot as slot  # noqa: F401

BASE = "/api/v1/discovery/machine/snapshots"
ROUTES = [("POST", "claim"), ("POST", "complete"), ("POST", "fail"), ("POST", "release"), ("GET", "summary")]
COUNT_FIELDS: Final = ("pending_ready", "claimed", "failed", "translated", "stale", "skipped")
BLOCKS: Final = [
    {"kind": "h1", "text": "Kindergeld"},
    {"kind": "p", "text": "Antrag stellen"},
    {"kind": "row", "cells": ["Frist", "4 Wochen"]},
]


@pytest.fixture
def api(slot: StoreSlot, client: TestClient[Litestar]) -> Iterator[TestClient[Litestar]]:  # noqa: F811
    """The shared machine test client, built after the store override is in place."""
    yield client


def _headers(db_session: Session) -> dict[str, str]:
    return {"X-API-Key": _issue_key(db_session)}


def _memory(slot: StoreSlot) -> InMemoryObjectStore:
    assert isinstance(slot.store, InMemoryObjectStore)
    return slot.store


def _claim(api: TestClient[Litestar], headers: dict[str, str], limit: int = 5) -> list[dict[str, object]]:
    response = api.post(f"{BASE}/claim", json={"limit": limit}, headers=headers)
    assert response.status_code == 200
    return list(response.json()["items"])


def _complete(
    api: TestClient[Litestar], headers: dict[str, str], items: list[dict[str, object]]
) -> list[dict[str, object]]:
    response = api.post(f"{BASE}/complete", json={"items": items}, headers=headers)
    assert response.status_code == 200
    return list(response.json()["items"])


def translated_item(served: dict[str, object], **fields: object) -> dict[str, object]:
    """Return the item a worker posts for ``served`` when it translated the page."""
    base: dict[str, object] = {
        "task_id": served["task_id"],
        "artifact_sha256": served["artifact_sha256"],
        "source_hash": HASH_NEW,
        "outcome": "translated",
        "blocks": BLOCKS,
        "truncated": False,
        "engine": "azure-translator",
        "model": None,
    }
    return base | fields


def unchanged_item(served: dict[str, object], source_hash: str) -> dict[str, object]:
    """Return the item a worker posts for ``served`` when the cleaned text did not change."""
    return {
        "task_id": served["task_id"],
        "artifact_sha256": served["artifact_sha256"],
        "source_hash": source_hash,
        "outcome": "unchanged",
    }


def skipped_item(served: dict[str, object], reason: str | None) -> dict[str, object]:
    """Return the item a worker posts for ``served`` when the page is not translated."""
    return {
        "task_id": served["task_id"],
        "artifact_sha256": served["artifact_sha256"],
        "source_hash": HASH_NEW,
        "outcome": "skipped",
        "skipped_reason": reason,
    }


@pytest.mark.parametrize(("method", "route"), ROUTES)
def test_a_missing_or_wrong_api_key_is_refused(
    api: TestClient[Litestar], db_session: Session, method: str, route: str
) -> None:
    """Auth · a wrong API key is refused with 401, and so is a missing one, on every snapshot route."""
    body = {} if method == "POST" else None

    missing = api.request(method, f"{BASE}/{route}", json=body)
    wrong = api.request(method, f"{BASE}/{route}", json=body, headers={"X-API-Key": "not-a-key"})

    assert (missing.status_code, wrong.status_code) == (401, 401)


def test_claim_returns_references_stamps_the_artifact_onto_the_task_and_carries_the_stored_hash(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Claim · returns references, stamps artifact_id and sha onto the task, and carries stored_source_hash."""
    page = queue_page(db_session)
    stored_row(db_session, page.catalogue, source_hash=HASH_STORED)

    (item,) = _claim(api, _headers(db_session))

    assert item["task_id"] == str(page.task.id)
    assert (item["catalogue_service_id"], item["locale"], item["source_locale"]) == (
        str(page.catalogue.id),
        "en",
        "de",
    )
    assert (item["artifact_id"], item["artifact_sha256"], item["source_url"]) == (
        str(page.artifact.id),
        SHA_A,
        SOURCE_URL,
    )
    assert item["stored_source_hash"] == HASH_STORED
    assert item["lease_expires_at"]
    (task,) = task_rows(db_session, page.catalogue.id)
    assert (task.artifact_id, task.artifact_sha256, task.status) == (page.artifact.id, SHA_A, WorkTaskStatus.CLAIMED)


@pytest.mark.parametrize("limit", [0, 6])
def test_claim_refuses_a_limit_outside_one_to_five_with_422(
    api: TestClient[Litestar], db_session: Session, limit: int
) -> None:
    """Claim · a limit outside one to five is refused with 422."""
    queue_page(db_session)

    response = api.post(f"{BASE}/claim", json={"limit": limit}, headers=_headers(db_session))

    assert response.status_code == 422


def test_claim_carries_a_null_stored_hash_for_a_page_never_translated(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Claim · a page with no stored translation carries a null stored_source_hash."""
    queue_page(db_session)

    (item,) = _claim(api, _headers(db_session))

    assert item["stored_source_hash"] is None


def test_claim_stamps_the_newest_snapshot_and_not_an_older_one(api: TestClient[Litestar], db_session: Session) -> None:
    """Claim · the newest snapshot of the page is the one stamped, however many older ones exist."""
    page = queue_page(db_session)
    newest = add_snapshot(db_session, page.catalogue, sha=SHA_B, fetched_at=NOW)

    (item,) = _claim(api, _headers(db_session))

    assert (item["artifact_id"], item["artifact_sha256"]) == (str(newest.id), SHA_B)


def test_claim_fails_a_page_with_no_snapshot_with_no_snapshot(api: TestClient[Litestar], db_session: Session) -> None:
    """Claim · a catalogue row with no snapshot fails the task with no_snapshot."""
    bare = catalogue_row(db_session)
    TaskRepository(db_session).upsert_snapshot_pending((bare.id, "en"), SHA_A, 100)

    assert _claim(api, _headers(db_session)) == []
    (task,) = task_rows(db_session, bare.id)
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, "no_snapshot")


def test_complete_translated_stores_the_object_updates_the_index_row_and_answers_stored(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · translated stores the object and updates the index row; answer stored."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    (answer,) = _complete(api, headers, [translated_item(served, truncated=True, model="m")])

    assert answer == {"task_id": served["task_id"], "outcome": "stored", "reason": None}
    (key,) = _memory(slot).stored_keys()
    assert key.startswith(f"translations/v1/snapshots/{page.catalogue.id}/en/") and key.endswith(".json")
    assert json.loads(_memory(slot).get(key)) == {
        "blocks": BLOCKS,
        "engine": "azure-translator",
        "locale": "en",
        "model": "m",
        "schema": 1,
        "source_hash": HASH_NEW,
        "source_url": SOURCE_URL,
        "truncated": True,
        "unit": "snapshot",
    }
    row = index_row(db_session, page.catalogue.id)
    assert row is not None
    assert (row.artifact_sha256, row.source_hash, row.storage_key, row.truncated, row.skipped_reason) == (
        SHA_A,
        HASH_NEW,
        key,
        True,
        None,
    )
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.COMPLETED


def test_complete_unchanged_completes_with_no_object_write_and_answers_unchanged(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · unchanged completes with no object write; answer unchanged."""
    page = queue_page(db_session)
    before = stored_row(db_session, page.catalogue, source_hash=HASH_NEW, artifact_sha=SHA_OLD)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    assert served["stored_source_hash"] == HASH_NEW

    (answer,) = _complete(api, headers, [unchanged_item(served, HASH_NEW)])

    assert answer["outcome"] == "unchanged"
    assert _memory(slot).stored_keys() == []
    row = index_row(db_session, page.catalogue.id)
    assert row is not None
    assert (row.artifact_sha256, row.source_hash, row.storage_key) == (SHA_A, HASH_NEW, before.storage_key)
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.COMPLETED


def test_complete_unchanged_for_a_hash_the_index_does_not_hold_is_rejected_and_fails_the_task(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · unchanged for a hash the index does not hold is rejected; the task fails and nothing is written."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    (answer,) = _complete(api, headers, [unchanged_item(served, HASH_NEW)])

    assert answer["outcome"] == "rejected"
    assert _memory(slot).stored_keys() == []
    assert index_row(db_session, page.catalogue.id) is None
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.FAILED


def test_complete_skipped_writes_the_marker_row_and_completes_the_task(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · skipped writes the marker row with its reason, completes the task and writes no object."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    (answer,) = _complete(api, headers, [skipped_item(served, "too_short")])

    assert answer["outcome"] == "skipped"
    assert _memory(slot).stored_keys() == []
    row = index_row(db_session, page.catalogue.id)
    assert row is not None
    assert (row.skipped_reason, row.storage_key, row.artifact_sha256, row.source_hash) == (
        "too_short",
        None,
        SHA_A,
        HASH_NEW,
    )
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.COMPLETED


def test_complete_skipped_without_a_reason_is_rejected_and_fails_the_task(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Complete · a skipped item that names no reason is rejected and the task fails."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    (answer,) = _complete(api, headers, [skipped_item(served, None)])

    assert answer["outcome"] == "rejected"
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.FAILED


def test_complete_stale_artifact_answers_stale_requeues_the_task_and_stores_nothing(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · a stale artifact_sha256 answers stale and requeues the task; nothing is stored."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    add_snapshot(db_session, page.catalogue, sha=SHA_B, fetched_at=NOW)

    (answer,) = _complete(api, headers, [translated_item(served)])

    assert answer["outcome"] == "stale"
    assert _memory(slot).stored_keys() == []
    assert index_row(db_session, page.catalogue.id) is None
    tasks = task_rows(db_session, page.catalogue.id)
    assert sorted(task.status.value for task in tasks) == ["completed", "pending"]
    (requeued,) = [task for task in tasks if task.status is WorkTaskStatus.PENDING]
    assert (requeued.source_hash, requeued.priority) == (SHA_B, 100)


def test_complete_with_an_unavailable_object_store_answers_unavailable_and_releases_without_an_attempt(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · an unavailable object store answers unavailable and releases the task without an attempt."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    slot.store = None

    (answer,) = _complete(api, headers, [translated_item(served)])

    assert answer["outcome"] == "unavailable"
    (task,) = task_rows(db_session, page.catalogue.id)
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)
    assert index_row(db_session, page.catalogue.id) is None


def test_complete_a_block_over_4000_characters_answers_rejected(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · a block over 4,000 characters answers rejected and stores nothing."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    (answer,) = _complete(api, headers, [translated_item(served, blocks=[{"kind": "p", "text": "x" * 4001}])])

    assert answer["outcome"] == "rejected"
    assert _memory(slot).stored_keys() == []
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.FAILED


def test_complete_a_page_of_more_than_2000_blocks_answers_rejected(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · a page of more than 2,000 blocks answers rejected and stores nothing."""
    queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    blocks = [{"kind": "p", "text": "Satz"} for _ in range(2001)]

    (answer,) = _complete(api, headers, [translated_item(served, blocks=blocks)])

    assert answer["outcome"] == "rejected"
    assert _memory(slot).stored_keys() == []


def test_complete_refuses_a_sixth_item_in_one_request_with_422_and_accepts_five(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Complete · a sixth item in one request is refused with 422; five are the most one call carries."""
    headers = _headers(db_session)
    item = {"task_id": str(uuid.uuid4()), "artifact_sha256": SHA_A, "source_hash": HASH_NEW, "outcome": "unchanged"}

    five = api.post(f"{BASE}/complete", json={"items": [item] * 5}, headers=headers)
    six = api.post(f"{BASE}/complete", json={"items": [item] * 6}, headers=headers)

    assert (five.status_code, six.status_code) == (200, 422)


def test_a_completed_task_cannot_be_completed_again(
    api: TestClient[Litestar], db_session: Session, slot: StoreSlot
) -> None:
    """Complete · a completed task cannot be completed again; the second answer is rejected."""
    queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)
    (first,) = _complete(api, headers, [translated_item(served)])

    (second,) = _complete(api, headers, [translated_item(served)])

    assert (first["outcome"], second["outcome"]) == ("stored", "rejected")
    assert len(_memory(slot).stored_keys()) == 1


def test_fail_settles_the_claimed_task_and_refuses_one_the_key_does_not_hold(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Fail · a retryable failure of a claimed task re-pends it; a task the key does not hold answers 409."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    failed = api.post(
        f"{BASE}/fail", json={"task_id": served["task_id"], "error": "boom", "retryable": True}, headers=headers
    )
    refused = api.post(f"{BASE}/fail", json={"task_id": str(uuid.uuid4()), "error": "x"}, headers=headers)

    assert failed.status_code == 200
    assert failed.json() == {"task_id": served["task_id"], "status": "pending", "last_error": "boom"}
    assert refused.status_code == 409
    (task,) = task_rows(db_session, page.catalogue.id)
    assert task.status is WorkTaskStatus.PENDING


def test_release_hands_claimed_tasks_back_without_consuming_an_attempt(
    api: TestClient[Litestar], db_session: Session
) -> None:
    """Release · claimed tasks go back to the queue without consuming an attempt; other ids are skipped."""
    page = queue_page(db_session)
    headers = _headers(db_session)
    (served,) = _claim(api, headers)

    response = api.post(
        f"{BASE}/release",
        json={"task_ids": [served["task_id"], str(uuid.uuid4())], "reason": "budget"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["released"] == [served["task_id"]]
    assert len(response.json()["skipped"]) == 1
    (task,) = task_rows(db_session, page.catalogue.id)
    assert (task.status, task.attempt_count) == (WorkTaskStatus.PENDING, 0)


def test_summary_counts_per_locale_for_each_status(api: TestClient[Litestar], db_session: Session) -> None:
    """Summary · counts per locale for each status: pending, claimed, failed, translated, stale and skipped."""
    headers = _headers(db_session)
    task_in_state(db_session, catalogue_row(db_session), WorkTaskStatus.PENDING)
    task_in_state(db_session, catalogue_row(db_session), WorkTaskStatus.CLAIMED)
    task_in_state(db_session, catalogue_row(db_session), WorkTaskStatus.FAILED)
    stored_row(db_session, catalogue_row(db_session), artifact_sha=SHA_A)
    skipped_row(db_session, catalogue_row(db_session))
    replaced = catalogue_row(db_session)
    stored_row(db_session, replaced, artifact_sha=SHA_OLD)
    task_in_state(db_session, replaced, WorkTaskStatus.PENDING, source_hash=SHA_A)
    task_in_state(db_session, catalogue_row(db_session), WorkTaskStatus.PENDING, locale="tr")

    body = api.get(f"{BASE}/summary", headers=headers).json()

    by_locale = {row["locale"]: row for row in body["locales"]}
    assert {field: by_locale["en"][field] for field in COUNT_FIELDS} == {
        "pending_ready": 2,
        "claimed": 1,
        "failed": 1,
        "translated": 2,
        "stale": 1,
        "skipped": 1,
    }
    assert by_locale["tr"]["pending_ready"] == 1
