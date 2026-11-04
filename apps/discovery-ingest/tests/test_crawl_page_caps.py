"""Crawl page and record caps of the CKAN and PVOG clients, both spent through PageBudget."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.govdata.ckan import GovDataCkanClient
from discovery_ingest.pvog.client import PvogClient, _build_v7_url

GOVDATA_FIXTURES = Path(__file__).parent / "fixtures" / "govdata"
PVOG_FIXTURES = Path(__file__).parent / "fixtures" / "pvog"
PACKAGE_ID = "ozg-leistungen-und-zugehorige-onlinedienste"
CKAN_BASE = "https://ckan.test/api/3/action"
FEDERAL_ARS = "000000000000"
PVOG_BASE = "https://pvog.fitko.net/suchdienst/api"
_REAL_HTTPX_CLIENT = httpx.Client


def _ckan_client(monkeypatch: pytest.MonkeyPatch, fetched: list[str], rows_per_page: int) -> GovDataCkanClient:
    """A CKAN client whose feed returns ``rows_per_page`` rows on every page and records each feed URL."""
    package_show = json.loads((GOVDATA_FIXTURES / "package_show.json").read_text(encoding="utf-8"))
    ozg_page = json.loads((GOVDATA_FIXTURES / "ozg_page.json").read_text(encoding="utf-8"))
    ozg_page["content"] = (ozg_page["content"] * rows_per_page)[:rows_per_page]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith(f"/package_show?id={PACKAGE_ID}"):
            return httpx.Response(200, json=package_show)
        if "/open-pvog/000000000000" in url:
            fetched.append(url)
            return httpx.Response(200, json=ozg_page)
        return httpx.Response(404, text=f"unexpected url {url}")

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.govdata.ckan.httpx.Client", client_factory)
    return GovDataCkanClient(CKAN_BASE, PACKAGE_ID, scope_ars=FEDERAL_ARS)


def test_ckan_client_max_pages_zero_fetches_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """GovDataCkanClient · a zero page cap yields nothing and makes no feed request."""
    fetched: list[str] = []
    client = _ckan_client(monkeypatch, fetched, rows_per_page=2)

    assert list(client.iter_record_pages(max_pages=0, page_size=2)) == []
    assert fetched == []


def test_ckan_client_max_pages_two_fetches_two_full_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """GovDataCkanClient · a page cap of two fetches two pages when each page is full."""
    fetched: list[str] = []
    client = _ckan_client(monkeypatch, fetched, rows_per_page=2)

    pages = list(client.iter_record_pages(max_pages=2, page_size=2))

    assert [len(page) for page in pages] == [2, 2]
    assert len(fetched) == 2


def test_ckan_client_short_page_stops_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    """GovDataCkanClient · a page shorter than the page size is the last one, even with pages left."""
    fetched: list[str] = []
    client = _ckan_client(monkeypatch, fetched, rows_per_page=1)

    pages = list(client.iter_record_pages(max_pages=5, page_size=2))

    assert [len(page) for page in pages] == [1]
    assert len(fetched) == 1


def test_ckan_client_max_records_trims_mid_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """GovDataCkanClient · a record cap trims the page that crosses it and stops after it."""
    fetched: list[str] = []
    client = _ckan_client(monkeypatch, fetched, rows_per_page=2)

    pages = list(client.iter_record_pages(max_pages=5, page_size=2, max_records=3))

    assert [len(page) for page in pages] == [2, 1]
    assert len(fetched) == 2


def test_pvog_client_zero_max_pages_fetches_nothing() -> None:
    """PvogClient · a zero page cap makes no request, not even the bootstrap page."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(404)

    client = PvogClient(PVOG_BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert list(client.iter_records(ars=FEDERAL_ARS, max_pages=0)) == []
    assert requested == []


def test_pvog_client_one_max_page_is_spent_by_the_bootstrap_page() -> None:
    """PvogClient · a page cap of one is used up by the bootstrap page, so no search page is fetched."""
    bootstrap_url = _build_v7_url(PVOG_BASE, FEDERAL_ARS, personal_matter="Geburt", facades=True)
    bootstrap_body = json.loads((PVOG_FIXTURES / "facades_personal_matters.json").read_text(encoding="utf-8"))
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == bootstrap_url:
            return httpx.Response(200, json=bootstrap_body)
        return httpx.Response(404)

    client = PvogClient(PVOG_BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert list(client.iter_records(ars=FEDERAL_ARS, max_pages=1)) == []
    assert requested == [bootstrap_url]
