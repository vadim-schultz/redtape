"""The machine API client of the translation routes: method, path, body and the errors it raises (search-first C15)."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.translation_models import TranslationCompleteItem
from pydantic import SecretStr

from translate_fakes import API_KEY, TranslateApi, task, task_id

ID = uuid.UUID(task_id(0))


def _api(*numbers: int) -> TranslateApi:
    return TranslateApi([task(number) for number in numbers])


def test_claim_posts_the_limit_and_returns_the_leased_units() -> None:
    """translation api · claim sends only the limit and parses the German unit, locale and hash of each task."""
    api = _api(0, 1, 2)

    claimed = api.client().translations.claim(limit=2)

    assert api.bodies["claim"] == [{"limit": 2}]
    assert [item.task_id for item in claimed.items] == [uuid.UUID(task_id(0)), uuid.UUID(task_id(1))]
    first = claimed.items[0]
    assert (first.title, first.locale, first.source_locale, first.source_hash) == (
        "Reisepass beantragen 0",
        "en",
        "de",
        "hash-0",
    )


def test_complete_posts_the_text_with_engine_and_model_and_parses_every_outcome() -> None:
    """translation api · complete sends task id, hash, text, engine and model and parses all four outcomes."""
    api = _api(0, 1, 2, 3)
    for number, outcome in enumerate(("stale", "rejected", "unavailable"), start=1):
        api.outcomes[task_id(number)] = (outcome, "why")
    items = [
        TranslationCompleteItem(
            task_id=uuid.UUID(task_id(number)),
            source_hash=f"hash-{number}",
            title="T",
            description="D",
            engine="scripted",
            model="m",
        )
        for number in range(4)
    ]

    results = api.client().translations.complete(items)

    assert api.bodies["complete"][0]["items"][1] == {
        "task_id": task_id(1),
        "source_hash": "hash-1",
        "title": "T",
        "description": "D",
        "engine": "scripted",
        "model": "m",
    }
    assert [result.outcome for result in results.items] == ["stored", "stale", "rejected", "unavailable"]


def test_fail_release_and_summary_use_their_routes_and_the_summary_adds_up_the_locales() -> None:
    """translation api · fail, release and summary send the documented bodies; pending_ready sums the locales."""
    api = _api(0, 1)
    client = api.client()

    failed = client.translations.fail(ID, error="boom", retryable=True)
    released = client.translations.release([ID], "llm_quota: used up")
    summary = client.translations.summary()

    assert api.bodies["fail"] == [{"task_id": str(ID), "error": "boom", "retryable": True}]
    assert api.bodies["release"] == [{"task_ids": [str(ID)], "reason": "llm_quota: used up"}]
    assert (failed.status, released.released, summary.pending_ready) == ("pending", [ID], 2)


def test_the_summary_route_is_a_get_without_a_body() -> None:
    """translation api · summary reads without leasing: GET, no body."""
    seen: list[httpx.Request] = []
    api = _api(0)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return api.handler(request)

    client = DiscoveryIngestClient("https://redtape.test", SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    client.translations.summary()

    assert seen[0].method == "GET" and not seen[0].content and seen[0].url.path.endswith("/translations/summary")


def test_a_refusal_raises_the_machine_error_with_the_key_scrubbed() -> None:
    """translation api · a 409 (a task this key does not hold) raises with its status; the API key never appears."""
    api = _api(0)
    api.forced["fail"] = (409, f"not yours {API_KEY}")

    with pytest.raises(DiscoveryMachineApiError) as caught:
        api.client().translations.fail(ID, error="boom")

    assert caught.value.status_code == 409 and API_KEY not in str(caught.value) and "<redacted>" in str(caught.value)


def test_a_507_on_claim_is_recognised_as_the_database_limit() -> None:
    """translation api · the soft-limit refusal is flagged so the drain can stop with db_limit instead of failing."""
    api = _api(0)
    api.forced["claim"] = (507, json.dumps({"detail": "database_soft_limit"}))

    with pytest.raises(DiscoveryMachineApiError) as caught:
        api.client().translations.claim(limit=1)

    assert caught.value.is_database_limit
