"""The machine API client of the embedding routes: method, path, body and the errors it raises (search-first C6)."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.embedding_models import EmbeddingCompleteItem
from pydantic import SecretStr

from embed_fakes import API_KEY, MODEL, EmbedApi, task, task_id

ID = uuid.UUID(task_id(0))


def _api(*numbers: int) -> EmbedApi:
    return EmbedApi([task(number) for number in numbers])


def test_claim_posts_the_model_and_limit_and_returns_the_leased_tasks() -> None:
    """embedding api · claim sends the model and limit and parses the tasks with their text and hash."""
    api = _api(0, 1, 2)

    claimed = api.client().embeddings.claim(MODEL, limit=2)

    assert api.bodies["claim"] == [{"model": MODEL, "limit": 2}]
    assert [item.task_id for item in claimed.items] == [uuid.UUID(task_id(0)), uuid.UUID(task_id(1))]
    assert (claimed.items[0].text, claimed.items[0].text_hash, claimed.items[0].locale) == ("text-0", "hash-0", "de")


def test_complete_posts_the_vectors_and_returns_one_result_per_item() -> None:
    """embedding api · complete sends task id, hash, model and vector and parses stored, stale and rejected."""
    api = _api(0, 1)
    api.outcomes[task_id(1)] = ("stale", None)
    items = [
        EmbeddingCompleteItem(task_id=uuid.UUID(task_id(number)), text_hash=f"hash-{number}", model=MODEL, vector=[1.0])
        for number in (0, 1)
    ]

    results = api.client().embeddings.complete(items)

    assert api.bodies["complete"][0]["items"][1] == {
        "task_id": task_id(1),
        "text_hash": "hash-1",
        "model": MODEL,
        "vector": [1.0],
    }
    assert [result.outcome for result in results.items] == ["stored", "stale"]


def test_fail_release_and_summary_use_their_routes() -> None:
    """embedding api · fail, release and summary send the documented bodies and parse the answers."""
    api = _api(0)
    client = api.client()

    failed = client.embeddings.fail(ID, error="boom", retryable=True)
    released = client.embeddings.release([ID], "llm_quota: used up")
    summary = client.embeddings.summary(MODEL)

    assert api.bodies["fail"] == [{"task_id": str(ID), "error": "boom", "retryable": True}]
    assert api.bodies["release"] == [{"task_ids": [str(ID)], "reason": "llm_quota: used up"}]
    assert (failed.status, released.released, summary.pending_ready) == ("pending", [ID], 1)


def test_the_summary_route_is_a_get_with_the_model_as_a_query_parameter() -> None:
    """embedding api · summary reads without leasing: GET with ``model``."""
    seen: list[httpx.Request] = []
    api = _api(0)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return api.handler(request)

    client = DiscoveryIngestClient("https://redtape.test", SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    client.embeddings.summary(MODEL)

    assert seen[0].method == "GET" and seen[0].url.params["model"] == MODEL and not seen[0].content


def test_a_refusal_raises_the_machine_error_with_the_key_scrubbed() -> None:
    """embedding api · a 409 (a task this key does not hold) raises with its status; the API key never appears."""
    api = _api(0)
    api.forced["fail"] = (409, f"not yours {API_KEY}")

    with pytest.raises(DiscoveryMachineApiError) as caught:
        api.client().embeddings.fail(ID, error="boom")

    assert caught.value.status_code == 409 and API_KEY not in str(caught.value) and "<redacted>" in str(caught.value)


def test_a_507_on_claim_is_recognised_as_the_database_limit() -> None:
    """embedding api · the soft-limit refusal is flagged so the drain can stop with db_limit instead of failing."""
    api = _api(0)
    api.forced["claim"] = (507, json.dumps({"detail": "database_soft_limit"}))

    with pytest.raises(DiscoveryMachineApiError) as caught:
        api.client().embeddings.claim(MODEL, limit=1)

    assert caught.value.is_database_limit
