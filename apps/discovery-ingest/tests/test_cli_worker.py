"""worker drain CLI with browser kinds: the safety checks before claiming and the report fields (chapter 15, Loop C)."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from discovery_ingest.cli import main

from render_fakes import FakeApi, task_json

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "tok-SECRET-0123456789"
PAGE = "https://portal.example/service/1"
DRAIN = ["worker", "drain", "--kinds", "render_page", "--max-tasks", "5"]


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", TOKEN)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


def _api(monkeypatch: pytest.MonkeyPatch, tasks: int = 1) -> FakeApi:
    api = FakeApi([[task_json(uuid.uuid4(), PAGE) for _ in range(tasks)]])
    api.client(monkeypatch)
    return api


def _rendered(request: httpx.Request) -> httpx.Response:
    body = {"success": True, "result": "<p>x</p>", "meta": {"status": 200, "finalUrl": PAGE}}
    return httpx.Response(200, json=body, headers={"X-Browser-Ms-Used": "1500"})


def test_a_browser_kind_without_cloudflare_settings_fails_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · render_page without the Cloudflare variables exits 2 and claims nothing."""
    api = _api(monkeypatch)
    monkeypatch.delenv("CLOUDFLARE_BROWSER_API_TOKEN")

    code = main(DRAIN)

    assert code == 2 and api.batches and api.calls == []
    err = capsys.readouterr().err
    assert "CLOUDFLARE_BROWSER_API_TOKEN" in err and ACCOUNT_ID not in err


@pytest.mark.parametrize("storage", [False, None])
def test_a_browser_kind_without_artifact_storage_fails_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], storage: bool | None
) -> None:
    """worker drain · storage disabled or an unreadable status route exits 1 before claiming."""
    api = _api(monkeypatch)
    api.storage_enabled = bool(storage)
    api.status_http = 200 if storage is False else 500

    code = main(DRAIN)

    assert code == 1 and api.batches and api.calls == []
    assert "storage" in capsys.readouterr().err


def test_a_plain_drain_needs_neither_cloudflare_settings_nor_the_storage_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """worker drain · the default kinds never read Cloudflare settings or the artifact status."""
    api = FakeApi([[]])
    api.client(monkeypatch)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID")
    monkeypatch.delenv("CLOUDFLARE_BROWSER_API_TOKEN")

    assert main(["worker", "drain"]) == 0


def test_the_drain_report_includes_browser_seconds_released_and_the_run_records_the_stop(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · a rendered page shows browser_seconds_used; a 429 shows released and stop browser_quota."""
    api = _api(monkeypatch)
    api.cloudflare = _rendered
    assert main(DRAIN) == 0
    done = json.loads(capsys.readouterr().out)
    assert (done["browser_seconds_used"], done["released"], done["completed"]) == (1.5, 0, 1)

    limited = _api(monkeypatch, tasks=3)
    limited.cloudflare = lambda request: httpx.Response(
        429, json={"success": False, "errors": [{"code": 2002, "message": "today"}]}
    )
    assert main(DRAIN) == 0
    stopped = json.loads(capsys.readouterr().out)
    assert (stopped["stop_reason"], stopped["released"], stopped["succeeded"]) == ("browser_quota", 3, True)
    assert limited.finishes[0]["status"] == "succeeded" and limited.finishes[0]["stop_reason"] == "browser_quota"


def test_a_rejected_cloudflare_token_fails_the_run_and_the_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · a 401 from Cloudflare releases the batch, records a failed run and exits 1."""
    api = _api(monkeypatch, tasks=2)
    api.cloudflare = lambda request: httpx.Response(
        401, json={"success": False, "errors": [{"code": 10000, "message": "bad"}]}
    )

    code = main(DRAIN)

    report = json.loads(capsys.readouterr().out)
    assert code == 1 and (report["succeeded"], report["stop_reason"], report["released"]) == (False, "error", 2)
    assert api.finishes[0]["status"] == "failed" and "Cloudflare" in str(api.finishes[0]["error_detail"])
    assert TOKEN not in json.dumps(report)


@pytest.mark.parametrize("flags", [["--browser-budget-seconds", "0"], ["--browser-budget-seconds", "-5"]])
def test_a_non_positive_browser_budget_is_rejected_before_claiming(
    monkeypatch: pytest.MonkeyPatch, flags: list[str]
) -> None:
    """worker drain · --browser-budget-seconds must be positive; nothing is claimed."""
    api = _api(monkeypatch)

    assert main([*DRAIN, *flags]) == 2 and api.calls == []
