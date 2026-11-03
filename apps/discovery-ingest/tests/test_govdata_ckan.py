"""GovData CKAN client tests (federal open-pvog scope)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.govdata.ckan import (
    GovDataCkanClient,
    GovDataCkanError,
    _scope_open_pvog_url,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "govdata"
PACKAGE_ID = "ozg-leistungen-und-zugehorige-onlinedienste"
CKAN_BASE = "https://ckan.test/api/3/action"
_TEMPLATE = "https://ozg.test/api/public/v1/dash/open-pvog?order=asc&page=0&size=100"
_REAL_HTTPX_CLIENT = httpx.Client


def test_scope_open_pvog_url_inserts_federal_ars_and_narrows_include_flags() -> None:
    """scope_open_pvog_url · inserts ARS path and sets includeAbove/Below false."""
    scoped = _scope_open_pvog_url(_TEMPLATE, "000000000000")

    assert "/open-pvog/000000000000" in scoped
    assert "includeAbove=false" in scoped
    assert "includeBelow=false" in scoped


def test_scope_open_pvog_url_raises_when_path_missing_open_pvog() -> None:
    """scope_open_pvog_url · raises when URL has no open-pvog path."""
    with pytest.raises(GovDataCkanError, match="open-pvog"):
        _scope_open_pvog_url("https://ozg.test/api/public/v1/dash/other", "000000000000")


def test_ckan_client_requests_scoped_leistungen_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GovDataCkanClient · requests federal-scoped Leistungen page after package_show."""
    package_show = json.loads((FIXTURE_DIR / "package_show.json").read_text(encoding="utf-8"))
    ozg_page = json.loads((FIXTURE_DIR / "ozg_page.json").read_text(encoding="utf-8"))
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        url = str(request.url)
        if url.endswith(f"/package_show?id={PACKAGE_ID}"):
            return httpx.Response(200, json=package_show)
        if "/open-pvog/000000000000" in url:
            return httpx.Response(200, json=ozg_page)
        return httpx.Response(404, text=f"unexpected url {url}")

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.govdata.ckan.httpx.Client", client_factory)

    client = GovDataCkanClient(CKAN_BASE, PACKAGE_ID, scope_ars="000000000000")
    pages = list(client.iter_record_pages(max_pages=1, page_size=100))

    assert len(pages) == 1
    assert len(pages[0]) == 2
    leistungen_calls = [u for u in requested_urls if "open-pvog" in u]
    assert len(leistungen_calls) == 1
    assert "includeBelow=false" in leistungen_calls[0]


def test_ckan_client_raises_when_package_has_no_leistungen_resource() -> None:
    """GovDataCkanClient · raises when CKAN package has no Leistungen resource."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith(f"/package_show?id={PACKAGE_ID}"):
            return httpx.Response(
                200,
                json={"success": True, "result": {"resources": []}},
            )
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        scoped_client = GovDataCkanClient(
            CKAN_BASE,
            PACKAGE_ID,
            scope_ars="000000000000",
            http_client=http_client,
        )
        with pytest.raises(GovDataCkanError, match="Leistungen"):
            list(scoped_client.iter_record_pages(max_pages=1))


def _client(http_client: httpx.Client) -> GovDataCkanClient:
    return GovDataCkanClient(CKAN_BASE, PACKAGE_ID, scope_ars="000000000000", http_client=http_client)


def test_ckan_client_raises_its_own_error_on_a_connection_failure() -> None:
    """GovDataCkanClient · a transport failure raises GovDataCkanError, chaining the original cause."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client(httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(GovDataCkanError) as caught:
        client._fetch_package_show()

    assert isinstance(caught.value.__cause__, httpx.ConnectError)


def test_ckan_client_raises_its_own_error_on_invalid_json() -> None:
    """GovDataCkanClient · a body that is not JSON raises GovDataCkanError, not a bare ValueError."""
    client = _client(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="not json"))))

    with pytest.raises(GovDataCkanError, match="invalid JSON"):
        client._fetch_package_show()


def test_ckan_client_raises_its_own_error_on_a_non_object_payload() -> None:
    """GovDataCkanClient · a JSON array body raises GovDataCkanError, not a bare ValueError."""
    client = _client(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[]))))

    with pytest.raises(GovDataCkanError, match="expected JSON object"):
        client._fetch_package_show()


def test_ckan_client_keeps_the_http_status_message() -> None:
    """GovDataCkanClient · a 500 still raises GovDataCkanError with the same message shape as before."""
    client = _client(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))

    with pytest.raises(GovDataCkanError, match="GovData HTTP 500 for"):
        client._fetch_package_show()
