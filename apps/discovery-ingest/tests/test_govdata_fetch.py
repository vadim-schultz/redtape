"""GovData live fetch CLI tests (chapter discovery-online 3)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "govdata"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
DISCOVERY_BASE = "https://redtape.test"
CKAN_BASE = "https://ckan.test/api/3/action"
PACKAGE_ID = "ozg-leistungen-und-zugehorige-onlinedienste"
LEISTUNGEN_PAGE_URL = (
    "https://ozg.test/api/public/v1/dash/open-pvog/000000000000"
    "?order=asc&page=0&size=100&includeAbove=false&includeBelow=false"
)
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.govdata.ckan.httpx.Client", client_factory)


def test_govdata_fetch_maps_ckan_page_and_posts_batch_with_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """govdata fetch · maps CKAN page and posts batch with API key."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("GOVDATA_CKAN_BASE_URL", CKAN_BASE)
    monkeypatch.setenv("GOVDATA_PACKAGE_ID", PACKAGE_ID)

    package_show = json.loads((FIXTURE_DIR / "package_show.json").read_text(encoding="utf-8"))
    ozg_page = json.loads((FIXTURE_DIR / "ozg_page.json").read_text(encoding="utf-8"))
    discovery_captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.url.host == "redtape.test":
            discovery_captured["api_key"] = request.headers.get("X-API-Key")
            discovery_captured["body"] = json.loads(request.content.decode())
            return httpx.Response(201, json={"items": []})
        if url.endswith(f"/package_show?id={PACKAGE_ID}"):
            return httpx.Response(200, json=package_show)
        if "/open-pvog/000000000000" in url:
            return httpx.Response(200, json=ozg_page)
        return httpx.Response(404, text=f"unexpected url {url}")

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "govdata",
            "fetch",
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
            "--max-pages",
            "1",
        ],
    )

    assert exit_code == 0
    assert discovery_captured["api_key"] == "test-machine-key"
    body = discovery_captured["body"]
    assert isinstance(body, dict)
    items = body["items"]
    assert isinstance(items, list)
    assert items[0]["external_id"] == "govdata:leika:12345678901234"
    assert items[0]["source"] == "govdata"


def test_govdata_fetch_exits_1_when_ckan_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """govdata fetch · exits 1 when CKAN returns 500."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("GOVDATA_CKAN_BASE_URL", CKAN_BASE)
    monkeypatch.setenv("GOVDATA_PACKAGE_ID", PACKAGE_ID)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith(f"/package_show?id={PACKAGE_ID}"):
            return httpx.Response(500, text="internal error")
        return httpx.Response(404, text="not found")

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "govdata",
            "fetch",
            "--jurisdiction-id",
            str(FEDERAL_JURISDICTION),
        ],
    )

    assert exit_code == 1
