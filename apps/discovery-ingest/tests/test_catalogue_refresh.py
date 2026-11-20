"""Catalogue refresh: the weekly step re-enqueues stale pages as fetch_url under the week key, never past the bound."""

from __future__ import annotations

import pytest
from discovery_ingest.cli import main
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.operations.catalogue_refresh import refresh_bound, refresh_stale_fetches
from discovery_ingest.operations.requeue import Counts

from render_fakes import CATALOGUE_ID, STALE_INPUT_KEY, FakeApi, stale_row

URL_A = "https://portal.example/service/a"
URL_B = "https://portal.example/service/b"
CAPS = (150, 50)


def _url(n: int) -> str:
    return f"https://portal.example/service/{n}"


def _fetch_enqueues(api: FakeApi) -> list[dict[str, object]]:
    return [body for name, _, body in api.calls if name == "enqueue"]


def _install_cli(monkeypatch: pytest.MonkeyPatch, api: FakeApi) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    api.client(monkeypatch)


def test_a_stale_page_is_enqueued_once_as_a_fetch_under_the_week_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · happy: one stale page is enqueued once as fetch_url, keyed by the week, within the bound."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A)]

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=5, page_caps=CAPS)

    assert (counts.pages, counts.queued, counts.already_queued, counts.failed) == (1, 1, 0, 0)
    assert [(b["kind"], b["target_url"], b["input_key"], b["catalogue_service_id"]) for b in _fetch_enqueues(api)] == [
        ("fetch_url", URL_A, STALE_INPUT_KEY, str(CATALOGUE_ID))
    ]
    assert api.stale_queries == [{"limit": "5"}]


def test_a_zero_bound_enqueues_nothing_and_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: the default bound of 0 reads nothing and enqueues nothing, so the weekly run is unchanged."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A)]

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=0, page_caps=CAPS)

    assert counts == Counts()
    assert api.stale_queries == [] and api.calls == []


def test_the_bound_limits_the_pages_read_and_enqueued(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: five stale pages and a bound of two read two and enqueue exactly two."""
    api = FakeApi([])
    api.stale_rows = [stale_row(_url(n)) for n in range(5)]

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=2, page_caps=CAPS)

    assert counts.queued == 2
    assert api.stale_queries == [{"limit": "2"}]
    assert len(_fetch_enqueues(api)) == 2


def test_a_page_already_queued_under_the_week_key_is_counted_not_queued_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: an enqueue that the queue answers as created false adds no task and counts as already queued."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A)]
    api.enqueued.add(("fetch_url", URL_A, STALE_INPUT_KEY))

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=5, page_caps=CAPS)

    assert (counts.queued, counts.already_queued) == (0, 1)


def test_the_requested_bound_stands_when_it_is_under_both_weekly_caps() -> None:
    """catalogue refresh · happy: a request under both weekly page caps is the bound."""
    assert refresh_bound(10, page_caps=CAPS) == 10


def test_the_bound_never_exceeds_the_smaller_weekly_page_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: a request above the PVOG cap of 50 is clamped to 50, and no more than 50 are enqueued."""
    api = FakeApi([])
    api.stale_rows = [stale_row(_url(n)) for n in range(60)]

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=500, page_caps=CAPS)

    assert refresh_bound(500, page_caps=CAPS) == 50
    assert api.stale_queries == [{"limit": "50"}]
    assert counts.queued == 50


def test_a_refused_stale_read_raises_and_enqueues_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: a refused listing raises the API error, so the command fails and queues nothing."""
    api = FakeApi([])
    api.stale_status = 500

    with pytest.raises(DiscoveryMachineApiError):
        refresh_stale_fetches(api.client(monkeypatch), max_rows=5, page_caps=CAPS)
    assert _fetch_enqueues(api) == []


def test_a_refused_enqueue_is_counted_as_failed_and_the_run_goes_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """catalogue refresh · negative: an enqueue the API refuses counts as failed; the next page is still tried."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A), stale_row(URL_B)]
    api.enqueue_status = 503

    counts = refresh_stale_fetches(api.client(monkeypatch), max_rows=5, page_caps=CAPS)

    assert (counts.queued, counts.failed) == (0, 2)
    assert len(_fetch_enqueues(api)) == 2


def test_the_command_reports_the_bound_it_used_and_the_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """catalogue refresh command · happy: with a bound of five, one stale page is queued and the report names the bound."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A)]
    _install_cli(monkeypatch, api)

    code = main(["catalogue", "refresh", "--max-rows", "5"])

    assert code == 0
    assert capsys.readouterr().out.split() == ["bound=5", "pages=1", "queued=1", "already_queued=0", "failed=0"]


def test_the_command_with_no_bound_makes_no_request_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """catalogue refresh command · negative: run without --max-rows, the bound is zero, nothing is requested and the exit is 0."""
    api = FakeApi([])
    api.stale_rows = [stale_row(URL_A)]
    _install_cli(monkeypatch, api)

    code = main(["catalogue", "refresh"])

    assert code == 0
    assert capsys.readouterr().out.split() == ["bound=0", "pages=0", "queued=0", "already_queued=0", "failed=0"]
    assert api.stale_queries == [] and api.calls == []


def test_the_command_exits_one_when_the_stale_listing_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """catalogue refresh command · negative: a refused listing exits 1 with the command named on stderr."""
    api = FakeApi([])
    api.stale_status = 500
    _install_cli(monkeypatch, api)

    code = main(["catalogue", "refresh", "--max-rows", "5"])

    assert code == 1
    assert "catalogue refresh command failed" in capsys.readouterr().err
