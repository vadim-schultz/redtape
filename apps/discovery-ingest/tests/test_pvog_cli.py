"""PVOG CLI integration tests against discovery machine API (chapter 13)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pvog"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
DISCOVERY_BASE = "https://redtape.test"
PVOG_BASE = "https://pvog.fitko.net/suchdienst/api"
FEDERAL_ARS = "000000000000"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.pvog.client.httpx.Client", client_factory)


def test_pvog_cli_sends_mapped_batch_with_source_pvog(monkeypatch: pytest.MonkeyPatch) -> None:
    """pvog CLI · sends mapped batch with source pvog."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    pvog_pages = {
        f"{PVOG_BASE}/v7/servicedescriptions/{FEDERAL_ARS}": FIXTURE_DIR / "page1.json",
        f"{PVOG_BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=2": FIXTURE_DIR / "page3_empty.json",
    }
    discovery_captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "redtape.test":
            discovery_captured["api_key"] = request.headers.get("X-API-Key")
            discovery_captured["body"] = json.loads(request.content.decode())
            return httpx.Response(201, json={"items": []})
        path = pvog_pages.get(str(request.url))
        if path is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "pvog",
            "run",
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
        ],
    )

    assert exit_code == 0
    assert discovery_captured["api_key"] == "test-machine-key"
    body = discovery_captured["body"]
    assert isinstance(body, dict)
    items = body["items"]
    assert isinstance(items, list)
    assert items[0]["source"] == "pvog"
    assert items[0]["external_id"] == "pvog:PORTAL-BUND-01:OD-EXAMPLE-001"


def test_pvog_cli_exits_non_zero_on_422_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """pvog CLI · exits non-zero on 422 validation."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    pvog_pages = {
        f"{PVOG_BASE}/v7/servicedescriptions/{FEDERAL_ARS}": FIXTURE_DIR / "page1.json",
        f"{PVOG_BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=2": FIXTURE_DIR / "page3_empty.json",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "redtape.test":
            return httpx.Response(422, json={"detail": "validation error"})
        path = pvog_pages.get(str(request.url))
        if path is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "pvog",
            "run",
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
        ],
    )

    assert exit_code == 1
