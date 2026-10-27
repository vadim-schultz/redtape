"""The Cloudflare adapter: request shape, throttle, error table and screenshot handling (chapter 15, Loop A)."""

from __future__ import annotations

import base64
from collections.abc import Callable

import httpx
import pytest
from discovery_ingest.browser.client import MAX_SCREENSHOT_BYTES, CloudflareBrowserClient
from discovery_ingest.browser.errors import (
    BrowserAuthError,
    BrowserQuotaExceeded,
    BrowserRequestError,
    ScreenshotOversize,
)
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.config import load_browser_settings

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "tok-SECRET-0123456789"
USER_AGENT = "RedtapeBot/1.0 (+https://example.test/bot)"
PAGE = "https://portal.example/service/1"
Handler = Callable[[httpx.Request], httpx.Response]
JPEG = b"\xff\xd8\xff" + b"1" * 40


class Clock:
    """A fake clock whose sleep advances it."""

    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", TOKEN)


def _client(handler: Handler, clock: Clock | None = None) -> CloudflareBrowserClient:
    clock = clock or Clock()
    return CloudflareBrowserClient(
        load_browser_settings(),
        user_agent=USER_AGENT,
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        throttle=Throttle(11.0, clock=clock, sleep=clock.sleep),
        clock=clock,
    )


def _page(html: str = "<html>x</html>", *, status: int = 200, ms: str | None = "1500") -> httpx.Response:
    meta = {"status": status, "finalUrl": PAGE + "/final", "title": "T"}
    headers = {"X-Browser-Ms-Used": ms} if ms is not None else {}
    return httpx.Response(200, json={"success": True, "result": html, "meta": meta}, headers=headers)


def _error(status: int, code: int = 1, message: str = "no", **headers: str) -> httpx.Response:
    return httpx.Response(
        status, json={"success": False, "errors": [{"code": code, "message": message}]}, headers=headers
    )


def test_render_posts_the_url_with_the_identifying_user_agent_and_returns_html_and_ms_used() -> None:
    """render · posts url, goto options and user agent; returns html, ms_used, status and final url."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _page("<p>rendered</p>")

    page = _client(handler).render(PAGE)

    request = seen[0]
    assert str(request.url) == f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/browser-run/content"
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    body = httpx.Response(200, content=request.content).json()
    assert body == {
        "url": PAGE,
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 30000},
        "userAgent": USER_AGENT,
    }
    assert (page.html, page.ms_used, page.http_status, page.final_url) == (
        "<p>rendered</p>",
        1500,
        200,
        PAGE + "/final",
    )


def test_render_falls_back_to_the_measured_duration_when_the_ms_header_is_absent_or_unreadable() -> None:
    """render · ms_used is the measured duration without a readable X-Browser-Ms-Used; fractions round up."""
    clock = Clock()
    answers = iter([_page(ms=None), _page(ms="oops"), _page(ms="1200.2")])

    def handler(request: httpx.Request) -> httpx.Response:
        clock.now += 2.5
        return next(answers)

    client = _client(handler, clock)

    assert [client.render(PAGE).ms_used for _ in range(3)] == [2500, 2500, 1201]


def test_render_returns_the_target_status_without_judging_it() -> None:
    """render · a target 404 comes back in http_status; Cloudflare answered 200."""
    page = _client(lambda request: _page(status=404)).render(PAGE)

    assert page.http_status == 404


def test_two_calls_are_at_least_the_minimum_interval_apart() -> None:
    """render · the second call waits the interval after the first ended (fake clock records the sleep)."""
    clock = Clock()

    def handler(request: httpx.Request) -> httpx.Response:
        clock.now += 3.0
        return _page()

    client = _client(handler, clock)
    client.render(PAGE)
    client.render(PAGE)

    assert clock.sleeps == [11.0]


def test_a_rate_limit_429_is_retried_once_through_the_throttle() -> None:
    """render · code 2001 with a short Retry-After is retried after the interval; a second 429 raises."""
    clock = Clock()
    answers = iter([_error(429, 2001, "Rate limit exceeded", **{"Retry-After": "10"}), _page()])
    client = _client(lambda request: next(answers), clock)

    assert client.render(PAGE).html == "<html>x</html>"
    assert clock.sleeps == [11.0]

    again = _client(lambda request: _error(429, 2001, "Rate limit exceeded", **{"Retry-After": "10"}), Clock())
    with pytest.raises(BrowserQuotaExceeded) as caught:
        again.render(PAGE)
    assert caught.value.retry_after == 10.0


def test_any_other_429_raises_quota_exceeded_with_retry_after_and_is_not_retried() -> None:
    """render · the daily limit 429 raises BrowserQuotaExceeded at once."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _error(429, 2002, "Browser time limit exceeded for today", **{"Retry-After": "3600"})

    with pytest.raises(BrowserQuotaExceeded) as caught:
        _client(handler).render(PAGE)

    assert (caught.value.retry_after, len(calls)) == (3600.0, 1)


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_raise_the_auth_error(status: int) -> None:
    """render · 401 and 403 raise BrowserAuthError."""
    with pytest.raises(BrowserAuthError):
        _client(lambda request: _error(status)).render(PAGE)


def test_5xx_and_timeouts_are_retryable_and_other_4xx_is_permanent() -> None:
    """render · 5xx, timeout and connection errors are retryable; 4xx (422 code 5006) is permanent."""

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} {TOKEN}", request=request)

    outcomes = {
        "5xx": _client(lambda request: _error(502, 1, "bad gateway")),
        "timeout": _client(timeout),
        "connect": _client(refused),
        "4xx": _client(lambda request: _error(422, 5006, "Network connection closed.")),
    }
    retryable: dict[str, bool] = {}
    messages: list[str] = []
    for name, client in outcomes.items():
        with pytest.raises(BrowserRequestError) as caught:
            client.render(PAGE)
        retryable[name] = caught.value.retryable
        messages.append(str(caught.value))

    assert retryable == {"5xx": True, "timeout": True, "connect": True, "4xx": False}
    assert "5006" in messages[3] and "Network connection closed." in messages[3]
    assert all(TOKEN not in message and ACCOUNT_ID not in message for message in messages)


def test_a_200_without_a_result_is_a_permanent_error() -> None:
    """render · an unreadable envelope is a permanent BrowserRequestError."""
    client = _client(lambda request: httpx.Response(200, json={"success": False, "errors": []}))

    with pytest.raises(BrowserRequestError) as caught:
        client.render(PAGE)

    assert caught.value.retryable is False


def _snapshot(image: bytes, html: str | None = "<p>shot</p>") -> httpx.Response:
    result = {"screenshot": base64.b64encode(image).decode(), **({"content": html} if html is not None else {})}
    return httpx.Response(200, json={"success": True, "result": result}, headers={"X-Browser-Ms-Used": "4100"})


def test_screenshot_returns_bytes_content_type_and_the_dom_from_one_snapshot_call() -> None:
    """screenshot · one /snapshot call with content and screenshot formats yields the jpeg and the html."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _snapshot(JPEG)

    image = _client(handler).screenshot(PAGE)

    body = httpx.Response(200, content=seen[0].content).json()
    assert seen[0].url.path.endswith("/browser-run/snapshot")
    assert body["formats"] == ["content", "screenshot"]
    assert body["screenshotOptions"] == {"fullPage": True, "type": "jpeg", "quality": 80}
    assert body["viewport"] == {"width": 1280, "height": 800}
    assert (image.data, image.content_type, image.ms_used, image.html) == (JPEG, "image/jpeg", 4100, "<p>shot</p>")


def test_an_over_limit_screenshot_is_rejected_and_a_broken_image_is_an_error() -> None:
    """screenshot · over 8 MB raises ScreenshotOversize; a result that is not base64 is a permanent error."""
    big = b"\xff\xd8\xff" + b"0" * MAX_SCREENSHOT_BYTES
    with pytest.raises(ScreenshotOversize) as caught:
        _client(lambda request: _snapshot(big)).screenshot(PAGE)
    assert caught.value.byte_size == len(big)

    broken = httpx.Response(200, json={"success": True, "result": {"screenshot": "***", "content": "x"}})
    with pytest.raises(BrowserRequestError):
        _client(lambda request: broken).screenshot(PAGE)
