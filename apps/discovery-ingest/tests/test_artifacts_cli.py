"""``artifacts list`` and ``artifacts download``: how a developer gets stored snapshots as fixtures (chapter 17, Loop D)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]
HTML = "<html><body>Bürger</body></html>".encode()


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], list[httpx.Request]]:
    """Install a handler behind every machine client call; return the list of requests it saw."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    def install(handler: Handler) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(recording)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
        return seen

    return install


def _artifact(index: int) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid.UUID(int=index)),
        "catalogue_service_id": str(uuid.uuid4()),
        "discovery_task_id": None,
        "kind": "html_snapshot",
        "storage_key": f"k{index}",
        "sha256": "abc",
        "content_type": "text/html",
        "byte_size": 100 + index,
        "source_url": f"https://verwaltung.bund.de/page/{index}",
        "final_url": None,
        "fetched_at": now,
        "created_at": now,
    }


def _listing(total: int) -> Handler:
    """Serve ``total`` artifacts, paged by the ``offset`` and ``limit`` query parameters."""

    def handler(request: httpx.Request) -> httpx.Response:
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        items = [_artifact(i) for i in range(offset, min(offset + limit, total))]
        return httpx.Response(200, json={"items": items, "total": total, "offset": offset, "limit": limit})

    return handler


def test_artifacts_list_prints_one_tab_separated_line_per_snapshot_of_the_host(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    """artifacts list · asks for html snapshots of the host and prints id, kind, size and source url per line."""
    seen = serve(_listing(3))

    assert main(["artifacts", "list", "--host", "verwaltung.bund.de", "--limit", "2"]) == 0

    lines = [line.split("\t") for line in capsys.readouterr().out.splitlines()]
    assert lines == [
        [str(uuid.UUID(int=0)), "html_snapshot", "100", "https://verwaltung.bund.de/page/0"],
        [str(uuid.UUID(int=1)), "html_snapshot", "101", "https://verwaltung.bund.de/page/1"],
    ]
    params = seen[0].url.params
    assert (params["host"], params["kind"], params["limit"], params["offset"]) == (
        "verwaltung.bund.de",
        "html_snapshot",
        "2",
        "0",
    )
    assert seen[0].headers["x-api-key"] == "test-machine-key"


def test_artifacts_list_pages_through_the_route_when_the_limit_exceeds_a_page(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    """artifacts list · a limit above 100 takes several requests and stops at the limit or the last page."""
    seen = serve(_listing(130))

    assert main(["artifacts", "list", "--host", "h.example", "--limit", "150"]) == 0

    assert len(capsys.readouterr().out.splitlines()) == 130
    assert [(r.url.params["offset"], r.url.params["limit"]) for r in seen] == [("0", "100"), ("100", "50")]


@pytest.mark.parametrize("argv", [["--limit", "0"], ["--limit", "x"], []])
def test_artifacts_list_rejects_a_missing_host_or_a_bad_limit_without_a_request(
    serve: Callable[[Handler], list[httpx.Request]], argv: list[str]
) -> None:
    """artifacts list · argument errors exit 2 before any API call."""
    seen = serve(_listing(1))
    host = [] if argv == [] else ["--host", "h.example"]

    with pytest.raises(SystemExit) as exit_info:
        main(["artifacts", "list", *host, *argv])

    assert exit_info.value.code == 2 and seen == []


def test_artifacts_list_exits_1_with_the_api_message_and_prints_nothing_on_a_refusal(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    """artifacts list · a 401 is exit 1, message on stderr, nothing on stdout."""
    serve(lambda request: httpx.Response(401, text="bad key"))

    assert main(["artifacts", "list", "--host", "h.example"]) == 1

    captured = capsys.readouterr()
    assert captured.out == "" and "401" in captured.err


def test_artifacts_download_writes_the_stored_bytes_to_the_output_path(
    serve: Callable[[Handler], list[httpx.Request]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """artifacts download · fetches the content route and writes the exact bytes, creating parent directories."""
    artifact_id = uuid.uuid4()
    seen = serve(lambda request: httpx.Response(200, content=HTML, headers={"content-type": "text/html"}))
    out = tmp_path / "fixtures" / "page.html"

    assert main(["artifacts", "download", "--id", str(artifact_id), "--out", str(out)]) == 0

    assert out.read_bytes() == HTML
    assert seen[0].url.path == f"/api/v1/discovery/machine/artifacts/{artifact_id}/content"
    assert str(out) in capsys.readouterr().out


@pytest.mark.parametrize("status", [404, 503])
def test_artifacts_download_exits_1_and_writes_no_file_when_the_artifact_is_unavailable(
    serve: Callable[[Handler], list[httpx.Request]], tmp_path: Path, capsys: pytest.CaptureFixture[str], status: int
) -> None:
    """artifacts download · an unknown artifact or unset store is exit 1 with the API message and no file."""
    serve(lambda request: httpx.Response(status, text=json.dumps({"detail": "Discovery artifact not found"})))
    out = tmp_path / "page.html"

    assert main(["artifacts", "download", "--id", str(uuid.uuid4()), "--out", str(out)]) == 1

    assert not out.exists() and str(status) in capsys.readouterr().err


def test_artifacts_download_rejects_an_id_that_is_not_a_uuid(
    serve: Callable[[Handler], list[httpx.Request]], tmp_path: Path
) -> None:
    """artifacts download · a malformed id exits 2 before any API call."""
    seen = serve(lambda request: httpx.Response(200, content=HTML))

    with pytest.raises(SystemExit) as exit_info:
        main(["artifacts", "download", "--id", "nope", "--out", str(tmp_path / "x.html")])

    assert exit_info.value.code == 2 and seen == []
