"""PoliteUrlFetcher behaviour against ``httpx.MockTransport`` (no real network)."""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterator

import httpx
import pytest
from discovery_ingest.worker.addresses import is_public_address
from discovery_ingest.worker.fetcher import FetchOutcome, PoliteUrlFetcher

Handler = Callable[[httpx.Request], httpx.Response]

PAGE = "https://portal.example/old"


def _fetcher(handler: Handler, **kwargs: object) -> PoliteUrlFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteUrlFetcher(min_interval_per_host_s=0, http_client=client, **kwargs)  # type: ignore[arg-type]


def _without_robots(handler: Handler) -> Handler:
    """Serve a missing robots.txt so a test only exercises page requests."""

    def wrapped(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return handler(request)

    return wrapped


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

    outcome = _fetcher(_without_robots(handler)).get(PAGE)

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

    outcome = _fetcher(_without_robots(handler)).get(PAGE)

    _assert_failed(outcome, "too many redirects")
    assert len(requested) == 6


def test_fetcher_fails_on_a_redirect_loop() -> None:
    """fetcher fails on a redirect loop."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _redirect(302, "/b" if request.url.path == "/old" else "/old")

    outcome = _fetcher(_without_robots(handler)).get(PAGE)

    _assert_failed(outcome, "redirect loop")


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_fetcher_never_reports_an_unresolved_3xx_as_success(status: int) -> None:
    """fetcher never reports an unresolved 3xx as success."""
    outcome = _fetcher(_without_robots(lambda _request: _redirect(status, None))).get(PAGE)

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


# Loop C: limits and guards

PUBLIC_IP = "93.184.216.34"


class _StaticResolver:
    """Resolver stub: hosts map to fixed addresses, unknown hosts resolve to a public one."""

    def __init__(self, addresses: dict[str, list[str]] | None = None) -> None:
        self._addresses = addresses or {}

    def resolve(self, host: str) -> list[str]:
        return self._addresses.get(host, [PUBLIC_IP])


def _guarded(handler: Handler, addresses: dict[str, list[str]] | None = None, **kwargs: object) -> PoliteUrlFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteUrlFetcher(
        min_interval_per_host_s=0,
        http_client=client,
        resolver=_StaticResolver(addresses),
        **kwargs,  # type: ignore[arg-type]
    )


def test_fetcher_aborts_a_response_larger_than_the_cap() -> None:
    """fetcher aborts a response larger than the cap and discards the partial body."""
    handler = _without_robots(lambda _request: httpx.Response(200, content=b"x" * 101))

    outcome = _guarded(handler, max_bytes=100).get("https://portal.example/big")

    _assert_failed(outcome, "exceeds 100 bytes")
    assert outcome.byte_length is None


def test_fetcher_accepts_a_response_exactly_at_the_cap() -> None:
    """fetcher accepts a response whose size equals the cap."""
    handler = _without_robots(lambda _request: httpx.Response(200, content=b"x" * 100))

    outcome = _guarded(handler, max_bytes=100).get("https://portal.example/edge")

    assert outcome.error_message is None
    assert outcome.byte_length == 100


def test_fetcher_stops_reading_once_the_cap_is_passed() -> None:
    """fetcher reads a stream only until the cap is passed."""
    chunks_read: list[int] = []

    def endless() -> Iterator[bytes]:
        for index in range(1000):
            chunks_read.append(index)
            yield b"x" * 10

    handler = _without_robots(lambda _request: httpx.Response(200, content=endless()))

    outcome = _guarded(handler, max_bytes=50).get("https://portal.example/endless")

    _assert_failed(outcome, "exceeds 50 bytes")
    assert len(chunks_read) <= 7


@pytest.mark.parametrize(
    "address",
    ["10.0.0.5", "127.0.0.1", "169.254.169.254", "192.168.1.1", "224.0.0.1", "240.0.0.1", "0.0.0.0", "::1", "fc00::1"],
)
def test_fetcher_rejects_a_host_that_resolves_to_a_non_public_address(address: str) -> None:
    """fetcher rejects private, loopback, link-local, multicast and reserved addresses."""
    site = _Site()

    outcome = _guarded(site, {"portal.example": [address]}).get("https://portal.example/page")

    _assert_failed(outcome, "non-public address")
    assert site.requests == []


def test_fetcher_rejects_a_host_when_any_resolved_address_is_non_public() -> None:
    """fetcher rejects a host with one public and one private address."""
    site = _Site()

    outcome = _guarded(site, {"portal.example": [PUBLIC_IP, "10.0.0.5"]}).get("https://portal.example/page")

    _assert_failed(outcome, "non-public address")
    assert site.requests == []


def test_fetcher_rejects_a_redirect_that_points_at_loopback() -> None:
    """fetcher validates every hop, so a redirect to 127.0.0.1 is never requested."""
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return _redirect(302, "http://127.0.0.1/admin")

    outcome = _guarded(handler).get(PAGE)

    _assert_failed(outcome, "non-public address")
    assert "127.0.0.1" not in hosts
    assert hosts == ["portal.example", "portal.example"]


def test_fetcher_rejects_an_unresolvable_host() -> None:
    """fetcher fails cleanly when the host does not resolve."""

    class Failing:
        def resolve(self, host: str) -> list[str]:
            raise socket.gaierror("name or service not known")

    client = httpx.Client(transport=httpx.MockTransport(_Site()))
    fetcher = PoliteUrlFetcher(min_interval_per_host_s=0, http_client=client, resolver=Failing())

    _assert_failed(fetcher.get(PAGE), "cannot resolve")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://portal.example/file", "gopher://portal.example/"])
def test_fetcher_rejects_non_http_schemes(url: str) -> None:
    """fetcher rejects file, ftp and other non-http schemes without a request."""
    site = _Site()

    outcome = _guarded(site).get(url)

    _assert_failed(outcome, "unsupported scheme")
    assert site.requests == []


def test_fetcher_rejects_a_redirect_to_a_non_http_scheme() -> None:
    """fetcher rejects a redirect that leaves http and https."""
    handler = _without_robots(lambda _request: _redirect(302, "ftp://portal.example/file"))

    _assert_failed(_guarded(handler).get(PAGE), "unsupported scheme")


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("93.184.216.34", True),
        ("8.8.8.8", True),
        ("2606:4700:4700::1111", True),
        ("10.1.2.3", False),
        ("172.16.0.1", False),
        ("100.64.0.1", False),
        ("::ffff:127.0.0.1", False),
        ("not-an-ip", False),
    ],
)
def test_is_public_address_classifies_addresses(address: str, expected: bool) -> None:
    """is_public_address accepts only globally routable unicast addresses."""
    assert is_public_address(address) is expected
