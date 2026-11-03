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

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)


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


def _export_with_payload(tmp_path: Path, raw_payload: dict[str, object]) -> Path:
    row = {"id": str(CATALOGUE_ID), "source": "pvog", "title_i18n": {"de": "Leistung"}, "raw_payload": raw_payload}
    path = tmp_path / "export.json"
    path.write_text(json.dumps({"items": [row]}), encoding="utf-8")
    return path


def _run_fim_enrich(export: Path) -> int:
    args = ["--catalogue-service-id", str(CATALOGUE_ID), "--catalogue-export", str(export)]
    return main(["fim", "enrich", *args, "--input", str(FIM_STECKBRIEF)])


@pytest.mark.parametrize("raw_payload", [{"leika_key": "99096049001001"}, {"leikakeys": ["99096049001001"]}])
def test_fim_enrich_cli_resolves_the_key_from_leika_key_and_leikakeys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raw_payload: dict[str, object],
) -> None:
    """fim enrich CLI · resolves the key from leika_key and leikakeys."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    posted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posted.append(request.url.path)
        body = json.loads(request.content.decode())
        reply = {"id": str(uuid.uuid4()), "catalogue_service_id": str(CATALOGUE_ID), "created": True}
        reply |= {
            "discovery_entity_id": str(uuid.uuid4()),
            "canonical_url": body.get("canonical_url"),
            "kind": "metadata",
        }
        return httpx.Response(201, json=reply)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    assert _run_fim_enrich(_export_with_payload(tmp_path, raw_payload)) == 0
    assert any(path.endswith("/entities") for path in posted)


def test_fim_enrich_cli_exits_1_without_a_well_formed_steckbrief_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """fim enrich CLI · exits 1 without a well-formed steckbrief key and posts nothing."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    _patch_httpx_client(monkeypatch, httpx.MockTransport(lambda _request: httpx.Response(500)))

    assert _run_fim_enrich(_export_with_payload(tmp_path, {"fim_id": "LB-EXAMPLE-STECK"})) == 1
    assert "no steckbrief key" in capsys.readouterr().err


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
