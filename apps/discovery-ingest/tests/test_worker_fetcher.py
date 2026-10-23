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


# Loop B: politeness

USER_AGENT = "RedtapeBot/1.0 (+https://github.com/vadim-schultz/redtape)"
ROBOTS = "https://portal.example/robots.txt"


class _Site:
    """Mock origin that serves a configurable robots.txt and records requests."""

    def __init__(self, robots: httpx.Response | None = None) -> None:
        self.robots = robots if robots is not None else httpx.Response(404)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/robots.txt":
            return self.robots
        return httpx.Response(200, content=b"page")

    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


def _disallow(path: str) -> httpx.Response:
    return httpx.Response(200, text=f"User-agent: *\nDisallow: {path}\n")


def test_fetcher_sends_the_identifying_user_agent() -> None:
    """fetcher sends the identifying user agent on the page and robots.txt requests."""
    site = _Site()

    _fetcher(site).get("https://portal.example/page")

    assert site.paths() == ["/robots.txt", "/page"]
    assert {request.headers["user-agent"] for request in site.requests} == {USER_AGENT}


def test_fetcher_uses_the_configured_user_agent() -> None:
    """fetcher uses the user agent it was constructed with."""
    site = _Site()

    _fetcher(site, user_agent="RedtapeBot/1.0 (+https://ops.example/bot)").get("https://portal.example/page")

    assert {request.headers["user-agent"] for request in site.requests} == {"RedtapeBot/1.0 (+https://ops.example/bot)"}


def test_fetcher_skips_a_path_disallowed_by_robots() -> None:
    """fetcher skips a path disallowed by robots.txt."""
    site = _Site(_disallow("/private"))

    outcome = _fetcher(site).get("https://portal.example/private/form")

    _assert_failed(outcome, "robots.txt disallows")
    assert site.paths() == ["/robots.txt"]


def test_fetcher_fetches_an_allowed_path_next_to_a_disallowed_one() -> None:
    """fetcher fetches a path robots.txt does not disallow."""
    site = _Site(_disallow("/private"))

    outcome = _fetcher(site).get("https://portal.example/public")

    assert outcome.error_message is None
    assert site.paths() == ["/robots.txt", "/public"]


@pytest.mark.parametrize("status", [404, 410, 401, 403])
def test_fetcher_treats_a_client_error_on_robots_as_allowed(status: int) -> None:
    """fetcher treats a missing or refused robots.txt as allowed."""
    site = _Site(httpx.Response(status))

    outcome = _fetcher(site).get("https://portal.example/page")

    assert outcome.http_status == 200
    assert site.paths() == ["/robots.txt", "/page"]


@pytest.mark.parametrize("failure", [httpx.Response(503), httpx.ReadTimeout("slow")])
def test_fetcher_skips_the_host_when_robots_is_unavailable(failure: httpx.Response | Exception) -> None:
    """fetcher skips pages on a host whose robots.txt answers 5xx or times out."""

    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(failure, Exception):
            raise failure
        return failure

    outcome = _fetcher(handler).get("https://portal.example/page")

    _assert_failed(outcome, "robots.txt unavailable")


def test_fetcher_requests_robots_once_per_host() -> None:
    """fetcher caches robots.txt for the process."""
    site = _Site()
    fetcher = _fetcher(site)

    fetcher.get("https://portal.example/a")
    fetcher.get("https://portal.example/b")
    fetcher.get("https://other.example/c")

    assert [r.url.path for r in site.requests if r.url.path == "/robots.txt"] == ["/robots.txt", "/robots.txt"]
    assert sorted(r.url.host for r in site.requests if r.url.path == "/robots.txt") == [
        "other.example",
        "portal.example",
    ]


def test_fetcher_does_not_retry_robots_after_it_failed_this_run() -> None:
    """fetcher keeps a host with unavailable robots.txt skipped without asking again."""
    site = _Site(httpx.Response(503))
    fetcher = _fetcher(site)

    fetcher.get("https://portal.example/a")
    fetcher.get("https://portal.example/b")

    assert site.paths() == ["/robots.txt"]
