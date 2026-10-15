"""FIM and LeiKa enrich CLI tests (chapter 17)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures"
CATALOGUE_EXPORT = FIXTURE_DIR / "catalogue_export.json"
FIM_STECKBRIEF = FIXTURE_DIR / "fim" / "steckbrief.json"
LEIKA_STAMMTEXT = FIXTURE_DIR / "leika" / "stammtext.json"
CATALOGUE_ID = uuid.UUID("22222222-2222-2222-2222-222222222201")
UNKNOWN_CATALOGUE_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)


def test_fim_enrich_cli_posts_entity_and_claim_from_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """fim enrich CLI · posts entity and claim from fixture."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    posts: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        posts.append((request.url.path, body))
        if request.url.path.endswith("/entities"):
            return httpx.Response(
                201,
                json={
                    "id": "33333333-3333-3333-3333-333333333301",
                    "catalogue_service_id": str(CATALOGUE_ID),
                    "canonical_url": body["canonical_url"],
                    "created": True,
                },
            )
        return httpx.Response(
            201,
            json={
                "id": "44444444-4444-4444-4444-444444444401",
                "discovery_entity_id": "33333333-3333-3333-3333-333333333301",
                "kind": body["kind"],
            },
        )

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(
        [
            "fim",
            "enrich",
            "--catalogue-service-id",
            str(CATALOGUE_ID),
            "--catalogue-export",
            str(CATALOGUE_EXPORT),
            "--input",
            str(FIM_STECKBRIEF),
        ],
    )

    assert exit_code == 0
    entity_posts = [path for path, _ in posts if path.endswith("/entities")]
    claim_posts = [path for path, _ in posts if path.endswith("/claims")]
    assert len(entity_posts) == 1
    assert len(claim_posts) >= 1
    assert posts[0][1]["catalogue_service_id"] == str(CATALOGUE_ID)


def test_leika_enrich_cli_exits_1_when_catalogue_id_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """leika enrich CLI · exits 1 when catalogue id unknown."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    _patch_httpx_client(monkeypatch, transport)

    exit_code = main(
        [
            "leika",
            "enrich",
            "--catalogue-service-id",
            str(UNKNOWN_CATALOGUE_ID),
            "--catalogue-export",
            str(CATALOGUE_EXPORT),
            "--input",
            str(LEIKA_STAMMTEXT),
        ],
    )

    assert exit_code == 1
