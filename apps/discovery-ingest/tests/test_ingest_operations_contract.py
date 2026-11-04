"""Ingest commands through main() · stdout, stderr and exit codes that the operations layer must keep."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
GOVDATA = FIXTURES / "govdata"
PVOG = FIXTURES / "pvog"
API_BASE = "https://redtape.test"
JURISDICTION = "11111111-1111-1111-1111-111111111101"
CATALOGUE_ID = uuid.UUID("22222222-2222-2222-2222-222222222201")
_REAL_HTTPX_CLIENT = httpx.Client


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")


def _patch_api(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)


def _ozg_page(rows: list[dict[str, object]], path: Path) -> Path:
    path.write_text(json.dumps({"content": rows}), encoding="utf-8")
    return path


MAPPABLE = {"leika_key": "12345678901234", "leistungsname": "Beispiel", "url": "https://example.bund.de/a"}
UNMAPPABLE = {"leistungsname": "Ohne Kennung", "url": "https://example.bund.de/b"}


def test_govdata_run_prints_each_skip_then_no_mappable_rows_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """govdata run · skipped rows print before the no-mappable message, nothing reaches stdout, exit 1."""
    _patch_api(monkeypatch, lambda _request: httpx.Response(500))
    export = _ozg_page([UNMAPPABLE], tmp_path / "ozg.json")

    assert main(["govdata", "run", "--input", str(export), "--jurisdiction-id", JURISDICTION]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert lines[0].startswith("skip row: ")
    assert lines[-1] == "no mappable GovData rows"


def test_govdata_run_refused_post_exits_1_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """govdata run · a refused batch exits 1 with nothing on stdout; stderr names the command (finding C4)."""
    _patch_api(monkeypatch, lambda _request: httpx.Response(422, text="refused"))
    export = _ozg_page([MAPPABLE], tmp_path / "ozg.json")

    assert main(["govdata", "run", "--input", str(export), "--jurisdiction-id", JURISDICTION]) == 1
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("govdata command failed: ")


def test_govdata_fetch_posts_each_page_as_it_arrives(monkeypatch: pytest.MonkeyPatch) -> None:
    """govdata fetch · one batch per mappable feed page, posted before the next page is read."""
    package_show = json.loads((GOVDATA / "package_show.json").read_text(encoding="utf-8"))
    page_rows = json.loads((GOVDATA / "ozg_page.json").read_text(encoding="utf-8"))["content"]
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/package_show?id=ozg-leistungen-und-zugehorige-onlinedienste"):
            return httpx.Response(200, json=package_show)
        if "/open-pvog/" in url:
            page = int(request.url.params["page"])
            events.append(f"fetch:{page}")
            return httpx.Response(200, json={"content": page_rows if page < 2 else []})
        if url.endswith("/catalogue/batch"):
            events.append("post")
            return httpx.Response(201, json={"created": 1, "updated": 0})
        return httpx.Response(404)

    monkeypatch.setattr(
        "discovery_ingest.govdata.ckan.httpx.Client",
        lambda **kwargs: _REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    _patch_api(monkeypatch, handler)

    exit_code = main(["govdata", "fetch", "--jurisdiction-id", JURISDICTION, "--page-size", "2"])

    assert exit_code == 0
    assert events == ["fetch:0", "post", "fetch:1", "post", "fetch:2"]


def test_govdata_fetch_failure_names_the_source_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """govdata fetch · a failed CKAN request prints the source-failure message and exits 1."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    monkeypatch.setattr(
        "discovery_ingest.govdata.ckan.httpx.Client",
        lambda **kwargs: _REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    _patch_api(monkeypatch, handler)

    assert main(["govdata", "fetch", "--jurisdiction-id", JURISDICTION]) == 1
    err = capsys.readouterr().err
    assert err.startswith("govdata fetch failed: GovData HTTP 500 for ")


def test_pvog_run_posts_nothing_when_a_late_page_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """pvog run · every page is walked before the one post, so a late page failure posts nothing."""
    bootstrap = json.loads((PVOG / "facades_personal_matters.json").read_text(encoding="utf-8"))
    paged = json.loads((PVOG / "v7_page_paged_code.json").read_text(encoding="utf-8"))
    posts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "pvog.fitko.net":
            query = request.url.params
            if query.get("facades") == "true":
                return httpx.Response(200, json=bootstrap)
            if query.get("page") == "0":
                return httpx.Response(200, json=paged)
            return httpx.Response(500)
        posts.append(str(request.url))
        return httpx.Response(201, json={"created": 1, "updated": 0})

    _patch_api(monkeypatch, handler)

    assert main(["pvog", "run", "--jurisdiction-id", JURISDICTION]) == 1
    assert posts == []
    assert capsys.readouterr().err.startswith("PVOG Suchdienst HTTP 500")


def test_fim_enrich_fixture_mismatch_prints_the_fetch_message_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """fim enrich · a fixture for another key prints the fim fetch message and exits 1, posting nothing."""
    _patch_api(monkeypatch, lambda _request: httpx.Response(500))
    export = tmp_path / "export.json"
    row = {"id": str(CATALOGUE_ID), "source": "pvog", "raw_payload": {"fim_id": "99096049001001"}}
    export.write_text(json.dumps({"items": [row]}), encoding="utf-8")
    fixture = tmp_path / "steckbrief.json"
    fixture.write_text(json.dumps({"leistungsschluessel": "99154021000000"}), encoding="utf-8")

    exit_code = main(
        [
            "fim",
            "enrich",
            "--catalogue-service-id",
            str(CATALOGUE_ID),
            "--catalogue-export",
            str(export),
            "--input",
            str(fixture),
        ]
    )

    assert exit_code == 1
    assert capsys.readouterr().err.startswith("fim fetch failed: fixture key")


def test_leika_enrich_missing_segments_prints_the_lookup_message_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """leika enrich · a row without redaktion or leistung id prints the lookup message and exits 1."""
    _patch_api(monkeypatch, lambda _request: httpx.Response(500))
    export = tmp_path / "export.json"
    row = {"id": str(CATALOGUE_ID), "source": "leika", "raw_payload": {}}
    export.write_text(json.dumps({"items": [row]}), encoding="utf-8")
    fixture = FIXTURES / "leika" / "stammtext.json"

    exit_code = main(
        [
            "leika",
            "enrich",
            "--catalogue-service-id",
            str(CATALOGUE_ID),
            "--catalogue-export",
            str(export),
            "--input",
            str(fixture),
        ]
    )

    assert exit_code == 1
    assert capsys.readouterr().err == "catalogue row missing redaktion_id and leistung_id\n"


def test_worker_drain_omitted_max_tasks_keeps_the_default_claim_size(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · omitted --max-tasks keeps the default claim size."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/tasks/claim"):
            seen.append(json.loads(request.content.decode())["limit"])
            return httpx.Response(200, json={"items": []})
        if str(request.url).endswith("/tasks/summary"):
            return httpx.Response(200, json={"pending_ready": 0})
        if str(request.url).endswith("/machine/runs"):
            return httpx.Response(201, json={"id": str(uuid.uuid4()), "kind": "worker_drain", "status": "running"})
        if "/finish" in str(request.url):
            return httpx.Response(200, json={"id": str(uuid.uuid4()), "kind": "worker_drain", "status": "succeeded"})
        return httpx.Response(200, json={"remaining": 0, "limit": 0, "used": 0, "ledger": "ok"})

    seen: list[int] = []
    _patch_api(monkeypatch, handler)

    assert main(["worker", "drain"]) == 0
    assert seen == [50]
    report = json.loads(capsys.readouterr().out)
    assert report["stop_reason"] == "queue_empty"


def test_worker_drain_zero_max_tasks_exits_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · explicit zero is a usage error and sends no claim request."""
    claim_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/tasks/claim"):
            claim_requests.append(request)
            return httpx.Response(200, json={"items": []})
        if url.endswith("/tasks/summary"):
            return httpx.Response(200, json={"pending_ready": 0})
        if url.endswith("/machine/runs"):
            return httpx.Response(201, json={"id": str(uuid.uuid4()), "kind": "worker_drain", "status": "running"})
        if "/finish" in url:
            return httpx.Response(200, json={"id": str(uuid.uuid4()), "kind": "worker_drain", "status": "succeeded"})
        return httpx.Response(200, json={"remaining": 0, "limit": 0, "used": 0, "ledger": "ok"})

    _patch_api(monkeypatch, handler)

    assert main(["worker", "drain", "--max-tasks", "0"]) == 2
    assert claim_requests == []
    assert "invalid drain bounds" in capsys.readouterr().err
