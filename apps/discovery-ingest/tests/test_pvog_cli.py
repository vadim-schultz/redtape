"""PVOG CLI integration tests against discovery machine API (chapter 13)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.pvog.client import _build_v7_url

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pvog"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
DISCOVERY_BASE = "https://redtape.test"
PVOG_BASE = "https://pvog.fitko.net/suchdienst/api"
FEDERAL_ARS = "000000000000"
_REAL_HTTPX_CLIENT = httpx.Client


def _bootstrap_url() -> str:
    return _build_v7_url(PVOG_BASE, FEDERAL_ARS, personal_matter="Geburt", facades=True)


def _search_url(code: str, page: int = 0) -> str:
    return _build_v7_url(PVOG_BASE, FEDERAL_ARS, personal_matter=code, facades=False, page=page)


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.pvog.client.httpx.Client", client_factory)


def _cli_pvog_pages() -> dict[str, Path]:
    return {
        _bootstrap_url(): FIXTURE_DIR / "facades_cli_single_leaf.json",
        _search_url("CLI_LEAF"): FIXTURE_DIR / "v7_page_cli_single.json",
    }


def test_pvog_cli_sends_mapped_batch_with_source_pvog(monkeypatch: pytest.MonkeyPatch) -> None:
    """pvog CLI · sends mapped batch with source pvog."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    pvog_pages = _cli_pvog_pages()
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
    assert items[0]["external_id"] == "pvog:leika:99001040001000"
    assert items[0]["portal_url"] == "https://service.example.bund.de/online"


def test_pvog_cli_exits_nonzero_on_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """pvog CLI · exits non-zero when PVOG Suchdienst returns 400."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "redtape.test":
            return httpx.Response(201, json={"items": []})
        return httpx.Response(400, json={"code": 1901, "message": "search criteria required"})

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


def test_pvog_vocabulary_prints_the_error_and_exits_1_on_a_connection_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """pvog CLI · a PVOG connection failure prints a message and exits 1, never a bare traceback."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(["pvog", "vocabulary"])

    assert exit_code == 1
    assert capsys.readouterr().err.strip() != ""


def test_pvog_cli_vocabulary_prints_sorted_leaf_codes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """pvog CLI · vocabulary prints the sorted leaf code list, one per line."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == _bootstrap_url():
            return httpx.Response(
                200,
                json=json.loads((FIXTURE_DIR / "facades_cli_single_leaf.json").read_text(encoding="utf-8")),
            )
        return httpx.Response(404, text="not found")

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(["pvog", "vocabulary"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip().splitlines() == ["CLI_LEAF"]


def test_pvog_cli_exits_non_zero_on_422_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """pvog CLI · exits non-zero on 422 validation."""
    monkeypatch.setenv("DISCOVERY_API_URL", DISCOVERY_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    pvog_pages = _cli_pvog_pages()

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
