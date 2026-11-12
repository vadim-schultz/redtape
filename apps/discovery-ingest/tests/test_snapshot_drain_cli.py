"""translate drain --unit snapshot and translate summary --unit snapshot: the bounds, the Azure settings, the counts, and the
characters the real adapter reports as billed."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from discovery_ingest.cli import main

from azure_transport import KEY as AZURE_KEY
from azure_transport import REGION, faithful_answer
from snapshot_fakes import SnapshotApi, page_html, snapshot_task
from translate_fakes import API_KEY

EXIT_USAGE = 2
EXIT_SKIP = 3


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", AZURE_KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)
    monkeypatch.delenv("AZURE_DOCUMENT_BUDGET_SHARE", raising=False)
    monkeypatch.setattr("discovery_ingest.operations.snapshot_drain.SNAPSHOT_MIN_INTERVAL_SECONDS", 0.0)
    yield


def test_drain_unit_snapshot_refuses_more_than_five_pages_a_claim_before_any_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · --unit snapshot takes at most five pages a claim; a larger value exits 2 before any request."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()})
    api.install(monkeypatch)

    code = main(["translate", "drain", "--unit", "snapshot", "--max-tasks", "10"])

    captured = capsys.readouterr()
    assert code == EXIT_USAGE and "between 1 and 5" in captured.err
    assert api.paths == []


def test_drain_unit_snapshot_without_azure_credentials_exits_2_naming_only_the_variable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · a missing Azure key exits 2 before any request, naming the variable and never its value."""
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY")
    api = SnapshotApi([snapshot_task(0)], {0: page_html()})
    api.install(monkeypatch)

    code = main(["translate", "drain", "--unit", "snapshot", "--max-tasks", "5"])

    captured = capsys.readouterr()
    assert code == EXIT_USAGE and "AZURE_TRANSLATOR_KEY" in captured.err
    assert AZURE_KEY not in captured.out + captured.err and api.paths == []


def test_drain_an_unknown_unit_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · --unit takes card or snapshot only; anything else is a usage error."""
    SnapshotApi([], {}).install(monkeypatch)

    assert main(["translate", "drain", "--unit", "bogus"]) == EXIT_USAGE


def test_summary_unit_snapshot_counts_snapshot_tasks_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate summary · --unit snapshot counts the page queue and never asks for the card queue."""
    api = SnapshotApi([snapshot_task(0), snapshot_task(1)], {})
    api.install(monkeypatch)

    code = main(["translate", "summary", "--unit", "snapshot"])

    data = json.loads(capsys.readouterr().out)
    assert code == 0 and data["pending_ready"] == 2
    assert [row["locale"] for row in data["locales"]] == ["en"]
    assert any(path.endswith("/snapshots/summary") for path in api.paths)
    assert not any(path.endswith("/translations/summary") for path in api.paths)


def test_summary_unit_snapshot_require_pending_exits_3_when_no_page_is_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate summary · --unit snapshot --require-pending exits 3 when no page is ready, so the workflow skips."""
    SnapshotApi([], {}).install(monkeypatch)

    assert main(["translate", "summary", "--unit", "snapshot", "--require-pending"]) == EXIT_SKIP
    assert "nothing to translate" in capsys.readouterr().err


def test_drain_unit_snapshot_settles_the_characters_azure_billed_through_the_real_adapter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · the real Azure adapter's billed characters (X-metered-usage) are the characters settled; no key printed."""
    api = SnapshotApi([snapshot_task(0, "en")], {0: page_html()})
    api.install(monkeypatch, lambda request: faithful_answer(request, metered=1234.0))

    code = main(["translate", "drain", "--unit", "snapshot", "--max-tasks", "5", "--max-batches", "2"])

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0
    assert (report["completed"], report["characters_used"], report["stop_reason"]) == (1, 1234, "queue_empty")
    assert api.posted()[0]["engine"] == "azure-translator"
    assert AZURE_KEY not in out and API_KEY not in out
