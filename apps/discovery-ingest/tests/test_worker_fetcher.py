"""PoliteUrlFetcher behaviour against ``httpx.MockTransport`` (no real network)."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from discovery_ingest.worker.fetcher import FetchOutcome, PoliteUrlFetcher

Handler = Callable[[httpx.Request], httpx.Response]

PAGE = "https://portal.example/old"


def _fetcher(handler: Handler, **kwargs: object) -> PoliteUrlFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteUrlFetcher(min_interval_per_host_s=0, http_client=client, **kwargs)  # type: ignore[arg-type]


def _redirect(status: int, location: str | None) -> httpx.Response:
    headers = {} if location is None else {"location": location}
    return httpx.Response(status, headers=headers)


def _assert_failed(outcome: FetchOutcome, message_part: str) -> None:
    assert outcome.body is None
    assert outcome.error_message is not None
    assert message_part in outcome.error_message


# Loop A: redirects


def test_fetcher_follows_a_301_to_a_200_and_reports_the_final_url() -> None:
    """fetcher follows a 301 to a 200 and reports the final url."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return _redirect(301, "/new")
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html/>")

    outcome = _fetcher(handler).get(PAGE)

    assert outcome.http_status == 200
    assert outcome.error_message is None
    assert outcome.final_url == "https://portal.example/new"
    assert outcome.redirect_count == 1
    assert outcome.body == b"<html/>"


def test_fetcher_fails_after_more_than_five_redirects() -> None:
    """fetcher fails after more than five redirects."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return _redirect(302, f"/hop{len(requested)}")

    outcome = _fetcher(handler).get(PAGE)

    _assert_failed(outcome, "too many redirects")
    assert len(requested) == 6


def test_fetcher_fails_on_a_redirect_loop() -> None:
    """fetcher fails on a redirect loop."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _redirect(302, "/b" if request.url.path == "/old" else "/old")

    outcome = _fetcher(handler).get(PAGE)

    _assert_failed(outcome, "redirect loop")


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_fetcher_never_reports_an_unresolved_3xx_as_success(status: int) -> None:
    """fetcher never reports an unresolved 3xx as success."""
    outcome = _fetcher(lambda _request: _redirect(status, None)).get(PAGE)

    _assert_failed(outcome, "Location")
    assert outcome.http_status == status
