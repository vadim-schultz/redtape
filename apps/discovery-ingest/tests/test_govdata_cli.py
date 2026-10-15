"""GovData CLI integration tests against discovery machine API (chapter 12)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "govdata" / "ozg_page.json"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)


def test_govdata_cli_posts_batch_to_machine_api_with_api_key_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """govdata CLI · posts batch to machine API with API key header."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["api_key"] = request.headers.get("X-API-Key")
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json={"items": []})

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "govdata",
            "run",
            "--input",
            str(FIXTURE),
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
        ],
    )

    assert exit_code == 0
    assert captured["api_key"] == "test-machine-key"
    assert captured["url"] == f"{API_BASE}/api/v1/discovery/machine/catalogue/batch"
    body = captured["body"]
    assert isinstance(body, dict)
    items = body["items"]
    assert isinstance(items, list)
    assert items[0]["external_id"] == "govdata:ozg:OZ-EXAMPLE-001"


def test_govdata_cli_exits_1_when_api_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """govdata CLI · exits 1 when API returns 401."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "bad-key")

    transport = httpx.MockTransport(
        lambda _request: httpx.Response(401, json={"detail": "Unauthorized"}),
    )
    _patch_httpx_client(monkeypatch, transport)

    exit_code = main(
        [
            "govdata",
            "run",
            "--input",
            str(FIXTURE),
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
        ],
    )

    assert exit_code == 1
