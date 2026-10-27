"""browser probe: a table per call, never the credentials, stops when Cloudflare refuses (chapter 15, Step 0)."""

from __future__ import annotations

import base64
from collections.abc import Callable

import httpx
import pytest
from discovery_ingest.browser.probe import ProbeReport, run_probe
from discovery_ingest.browser.probe_plan import ProbeCall, probe_plan
from discovery_ingest.browser.probe_report import report_lines
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.cli import main
from discovery_ingest.config import BrowserSettings, load_browser_settings

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "tok-SECRET-0123456789"
PAGE = "https://example.com/"
Handler = Callable[[httpx.Request], httpx.Response]
_REAL_HTTPX_CLIENT = httpx.Client


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DISCOVERY_API_URL", "DISCOVERY_API_KEY", "BROWSER_MIN_INTERVAL_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", TOKEN)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


class FakeClock:
    """A clock whose sleep advances it, so a test never waits."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _envelope(html: str = "<html>x</html>", status: int = 200) -> httpx.Response:
    meta = {"status": status, "finalUrl": PAGE, "title": "Example", "headers": {"server": "x"}}
    return httpx.Response(
        200, json={"success": True, "result": html, "meta": meta}, headers={"X-Browser-Ms-Used": "1234"}
    )


def _probe(
    handler: Handler, calls: list[ProbeCall], *, clock: FakeClock | None = None, max_ms: int = 10**9
) -> ProbeReport:
    clock = clock or FakeClock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        return run_probe(load_browser_settings(), calls, http=http, throttle=throttle, max_ms=max_ms)


def _calls(*urls: str, errors: tuple[str, ...] = ()) -> list[ProbeCall]:
    return probe_plan(urls, errors, user_agent="RedtapeBot/1.0", variants=("content",))


def test_probe_prints_a_table_row_per_call_and_never_prints_the_token() -> None:
    """probe · prints a table and never prints the token or the account id."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/content") and "bad" in request.content.decode():
            return httpx.Response(
                400, json={"success": False, "errors": [{"code": 1, "message": f"{TOKEN} {ACCOUNT_ID}"}]}
            )
        return _envelope()

    report = _probe(handler, _calls(PAGE, "https://bad.example/"))
    text = "\n".join(report_lines(report, load_browser_settings()))

    assert seen[0].headers["authorization"] == f"Bearer {TOKEN}"
    assert f"/accounts/{ACCOUNT_ID}/browser-run/content" in str(seen[0].url)
    assert "1234" in text and "status=200" in text and "meta.status=200" in text
    assert TOKEN not in text and ACCOUNT_ID not in text and "<redacted>" in text


def test_probe_redacts_a_transport_error_that_names_the_account_url() -> None:
    """probe · a transport error is reported without the account id in its url."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    report = _probe(handler, _calls(PAGE))
    text = "\n".join(report_lines(report, load_browser_settings()))

    assert "ConnectError" in text and ACCOUNT_ID not in text


def test_probe_exits_non_zero_when_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · exits non-zero when settings are missing and names only the variable."""
    monkeypatch.delenv("CLOUDFLARE_BROWSER_API_TOKEN")

    code = main(["browser", "probe", "--url", PAGE])

    assert code == 2
    err = capsys.readouterr().err
    assert "CLOUDFLARE_BROWSER_API_TOKEN" in err and ACCOUNT_ID not in err


def test_probe_needs_neither_the_discovery_api_url_nor_its_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · runs with only the two Cloudflare variables set."""

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(lambda _request: _envelope())
        return _REAL_HTTPX_CLIENT(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("discovery_ingest.browser.probe_cli.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.browser.probe_cli.plain_size", lambda _url: 577)

    code = main(["browser", "probe", "--url", PAGE, "--variant", "content"])

    assert code == 0
    assert "meta.status=200" in capsys.readouterr().out


def test_probe_stops_at_the_first_refusal_and_says_why() -> None:
    """probe · 401, 403 and 429 stop the probe; later calls are not made."""
    for status in (401, 403, 429):
        sent: list[httpx.Request] = []

        def handler(request: httpx.Request, status: int = status, sent: list[httpx.Request] = sent) -> httpx.Response:
            sent.append(request)
            return httpx.Response(
                status,
                headers={"Retry-After": "30"},
                json={"success": False, "errors": [{"code": status, "message": "no"}]},
            )

        report = _probe(handler, _calls(PAGE, "https://example.org/", "https://example.net/"))

        assert len(sent) == 1 and len(report.rows) == 1
        assert report.stopped is not None and str(status) in report.stopped
        assert "retry-after=30" in "\n".join(report_lines(report, load_browser_settings()))


def test_probe_stops_when_the_browser_time_cap_is_reached() -> None:
    """probe · stops once the summed X-Browser-Ms-Used passes the cap; the next call is never made."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _envelope()

    report = _probe(handler, _calls(PAGE, "https://example.org/", "https://example.net/"), max_ms=2000)

    assert len(sent) == 2 and report.total_ms == 2468
    assert report.stopped is not None and "browser time cap" in report.stopped


def test_probe_spaces_every_call_by_the_minimum_interval() -> None:
    """probe · each call starts the minimum interval after the previous one ended (3 s call + 11 s)."""
    clock = FakeClock()
    starts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        starts.append(clock.now)
        clock.now += 3
        return _envelope()

    _probe(handler, _calls(PAGE, "https://example.org/", "https://example.net/"), clock=clock)

    assert [b - a for a, b in zip(starts, starts[1:], strict=False)] == [14.0, 14.0]


def test_probe_describes_raw_and_enveloped_images_and_the_userAgent_echo() -> None:  # noqa: N802
    """probe · reports a raw image body, a base64 screenshot field and whether the userAgent was honoured."""
    jpeg = b"\xff\xd8\xff" + b"0" * 17

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        if request.url.path.endswith("/screenshot"):
            return httpx.Response(200, content=jpeg, headers={"content-type": "image/jpeg"})
        if request.url.path.endswith("/snapshot"):
            shot = base64.b64encode(jpeg).decode()
            return httpx.Response(200, json={"success": True, "result": {"content": "<p>x</p>", "screenshot": shot}})
        assert "navigator.userAgent" in body
        return _envelope("<html><body>RedtapeBot/1.0</body></html>")

    plan = probe_plan(
        (PAGE,), (), user_agent="RedtapeBot/1.0", variants=("ua-echo", "screenshot-jpeg", "snapshot-shot")
    )
    lines = "\n".join(report_lines(_probe(handler, plan), load_browser_settings()))

    assert "raw image/jpeg 20 B" in lines
    assert "result.screenshot=jpeg 20 B" in lines
    assert "userAgent echoed" in lines


def test_the_plan_runs_every_variant_once_per_page_and_only_content_for_error_urls() -> None:
    """probe · plan: pages get every variant once, error urls only the contract call, ua-echo has no url."""
    page, other, error = PAGE, "https://fimportal.de/", "https://example.com/missing"

    plan = probe_plan((page, other), (error,), user_agent="RedtapeBot/1.0", variants=None)
    keys = [(call.variant, call.target) for call in plan]

    assert len(keys) == len(set(keys))
    assert [call.variant for call in plan if call.target == error] == ["content"]
    assert [call.variant for call in plan if call.target == page] == [
        "content",
        "content-lean",
        "snapshot-md",
        "screenshot-jpeg",
        "screenshot-png",
        "snapshot-shot",
    ]
    assert plan[0].variant == "ua-echo" and [call.variant for call in plan].count("ua-echo") == 1


def test_the_plan_rejects_an_unknown_variant() -> None:
    """probe · plan: an unknown variant name is a ValueError, nothing is planned."""
    with pytest.raises(ValueError, match="unknown variant"):
        probe_plan((PAGE,), (), user_agent="x", variants=("nope",))


def test_browser_settings_report_the_missing_variables_without_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · BrowserSettings lists missing credential names and keeps the token out of its repr."""
    settings = load_browser_settings()
    assert isinstance(settings, BrowserSettings) and settings.missing_credentials() == []
    assert TOKEN not in repr(settings)

    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID")
    assert load_browser_settings().missing_credentials() == ["CLOUDFLARE_ACCOUNT_ID"]


def test_probe_reads_a_fractional_ms_header_and_shows_one_it_cannot_read() -> None:
    """probe · X-Browser-Ms-Used may be fractional (rounded up); an unreadable value is shown, not dropped."""
    values = iter(["1354.2", "n/a"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "result": "<p>"}, headers={"X-Browser-Ms-Used": next(values)})

    report = _probe(handler, _calls(PAGE, "https://example.org/"))
    text = "\n".join(report_lines(report, load_browser_settings()))

    assert [row.ms_used for row in report.rows] == [1355, None]
    assert "ms=1355" in text and "ms_header='n/a'" in text
