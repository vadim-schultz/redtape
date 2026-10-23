"""API health waiter tests for scheduled discovery ingest."""

from __future__ import annotations

import httpx
import pytest
from discovery_ingest.health import ApiHealthError, wait_for_api

API_BASE = "https://redtape.test"


def test_wait_for_api_returns_when_health_200() -> None:
    """wait_for_api · returns when health 200."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/deliberately-wrong"
        return httpx.Response(200, json={"status": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    wait_for_api(API_BASE, max_attempts=3, retry_delay_seconds=0, http_client=client)
    assert calls == 1


def test_wait_for_api_raises_after_max_retries_on_503() -> None:
    """wait_for_api · raises after max retries on 503."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, headers={"Retry-After": "5"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ApiHealthError, match="503"):
        wait_for_api(API_BASE, max_attempts=2, retry_delay_seconds=0, http_client=client)
