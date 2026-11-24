"""Canary runner: stable pages only, the fused call without the accept script, and the browser-time cap (chapter 8)."""

from __future__ import annotations

from discovery_ingest.browser.canary_run import CanaryRun, run_canary

from canary_fakes import FakeCanaryBrowser, page

JPEG = b"\xff\xd8\xff" + b"0" * 8
URL_A = "https://portal.example/service/a"
URL_B = "https://portal.example/service/b"
URL_C = "https://portal.example/service/c"


def test_an_unstable_page_is_skipped_and_a_stable_page_is_measured() -> None:
    """canary run · two /content renders that differ make the page unstable; the stable page is the one measured."""
    browser = FakeCanaryBrowser(
        renders={URL_A: [page("first"), page("second")], URL_B: [page("steady"), page("steady")]},
        fused={URL_B: page("steady")},
    )

    run = run_canary(browser, [URL_A, URL_B], required=1, max_ms=60_000)

    assert run.skipped == (URL_A,)
    assert [measured.identical for measured in run.pages] == [True]
    assert run.verdict.passed is True


def test_the_fused_call_sends_no_accept_script() -> None:
    """canary run · the fused /snapshot is asked for with consent_click off, so the accept script is not sent."""
    browser = FakeCanaryBrowser(renders={URL_B: [page("steady"), page("steady")]}, fused={URL_B: page("steady")})

    run_canary(browser, [URL_B], required=1, max_ms=60_000)

    assert browser.consent_clicks == [False]


def test_a_fused_dom_that_loses_the_text_fails_the_canary() -> None:
    """canary run · the fused DOM is missing the page's text: the run measures it and the verdict fails."""
    browser = FakeCanaryBrowser(
        renders={URL_B: [page("steady text here"), page("steady text here")]},
        fused={URL_B: page()},
    )

    run = run_canary(browser, [URL_B], required=1, max_ms=60_000)

    assert run.verdict.passed is False


def test_the_run_stops_when_the_browser_time_cap_is_spent_before_enough_pages() -> None:
    """canary run · 2 s per call and a 5 s cap: the run stops early, reports the cap and fails for missing pages."""
    steady = {URL_A: [page("a"), page("a")], URL_B: [page("b"), page("b")], URL_C: [page("c"), page("c")]}
    browser = FakeCanaryBrowser(renders=steady, fused={URL_A: page("a"), URL_B: page("b"), URL_C: page("c")}, ms=2000)

    run: CanaryRun = run_canary(browser, [URL_A, URL_B, URL_C], required=3, max_ms=5_000)

    assert run.stopped == "browser time cap reached"
    assert len(run.pages) < 3 and run.verdict.passed is False
    assert run.spent_ms >= 5_000
