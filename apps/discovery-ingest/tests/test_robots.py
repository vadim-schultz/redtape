"""RobotsCache and its two callers use the RFC 9309 matcher; status handling and failure wording are unchanged."""

from __future__ import annotations

import uuid

import httpx
import pytest
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.outcome import FetchFailure, FetchOutcome
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.robots import RobotsCache, RobotsUnavailableError

from render_fakes import FakeApi, FakeBrowser, page, robots_fetcher, task_json

HOST = "https://portal.example"
ALLOW_ONE_PAGE = "User-agent: *\nDisallow: /\nAllow: /Uebersicht\n"
ALLOWED_URL = f"{HOST}/Uebersicht"
BLOCKED_URL = f"{HOST}/Geheim"


def _answer(status: int, text: str = "") -> FetchOutcome:
    return FetchOutcome(status, "text/plain", len(text), None, body=text.encode())


def _cache(*answers: FetchOutcome) -> tuple[RobotsCache, list[str]]:
    requested: list[str] = []
    queue = list(answers)

    def fetch(url: str) -> FetchOutcome:
        requested.append(url)
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return RobotsCache(fetch), requested


def test_the_cache_decides_with_the_longest_match_not_the_first() -> None:
    """RobotsCache.allowed uses the new rules: the file's first rule is the shorter, wrong one."""
    cache, _ = _cache(_answer(200, ALLOW_ONE_PAGE))

    assert cache.allowed(ALLOWED_URL) is True
    assert cache.allowed(BLOCKED_URL) is False


def test_the_cache_honours_the_end_anchor() -> None:
    """RobotsCache.allowed blocks a file the star-and-dollar pattern forbids, which urllib let through."""
    cache, _ = _cache(_answer(200, "User-agent: *\nDisallow: /*.pdf$\n"))

    assert (cache.allowed(f"{HOST}/a.pdf"), cache.allowed(f"{HOST}/a.html")) == (False, True)


@pytest.mark.parametrize("status", [401, 403, 404, 410])
def test_a_4xx_robots_response_allows_everything(status: int) -> None:
    """a 4xx robots response allows everything (unchanged)."""
    cache, _ = _cache(_answer(status))

    assert cache.allowed(BLOCKED_URL) is True


@pytest.mark.parametrize("failure", [_answer(500), _answer(503), FetchOutcome(None, None, None, "timed out")])
def test_a_5xx_or_transport_failure_raises_and_is_cached_per_origin(failure: FetchOutcome) -> None:
    """a 5xx or transport failure raises RobotsUnavailableError and is cached per origin."""
    cache, requested = _cache(failure, _answer(200, ""))

    for _ in range(2):
        with pytest.raises(RobotsUnavailableError):
            cache.allowed(ALLOWED_URL)

    assert requested == [f"{HOST}/robots.txt"]


def test_rules_are_cached_per_origin() -> None:
    """each origin's robots.txt is fetched once and its rules do not leak to another origin."""
    cache, requested = _cache(_answer(200, ALLOW_ONE_PAGE), _answer(404))

    verdicts = [cache.allowed(BLOCKED_URL), cache.allowed(BLOCKED_URL), cache.allowed("https://other.example/Geheim")]

    assert verdicts == [False, False, True]
    assert requested == [f"{HOST}/robots.txt", "https://other.example/robots.txt"]


def _fetcher(robots: str) -> PoliteUrlFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=robots if request.url.path == "/robots.txt" else "page")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteUrlFetcher(min_interval_per_host_s=0, http_client=client)


def test_the_fetcher_reports_robots_disallowed_with_the_unchanged_message() -> None:
    """the fetcher reports ROBOTS_DISALLOWED with the message robots.txt disallows <url> for a blocked url."""
    fetcher = _fetcher(ALLOW_ONE_PAGE)

    blocked = fetcher.get(BLOCKED_URL)
    allowed = fetcher.get(ALLOWED_URL)

    assert blocked.error_message == f"robots.txt disallows {BLOCKED_URL}"
    assert (blocked.failure, blocked.retryable) == (FetchFailure.ROBOTS_DISALLOWED, False)
    assert allowed.error_message is None and allowed.body == b"page"


def _render(monkeypatch: pytest.MonkeyPatch, url: str) -> tuple[FakeApi, FakeBrowser]:
    api, browser = FakeApi([[task_json(uuid.uuid4(), url)]]), FakeBrowser(page("<p>x</p>"))
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=480)
    run_worker_drain(api.client(monkeypatch), robots_fetcher(ALLOW_ONE_PAGE), policy, browser=browser)
    return api, browser


def test_a_browser_task_with_a_blocked_url_fails_permanently(monkeypatch: pytest.MonkeyPatch) -> None:
    """a browser task with a blocked url fails permanently and the browser is never called."""
    api, browser = _render(monkeypatch, BLOCKED_URL)

    ((_, body),) = api.named("fail")
    assert body["retryable"] is False and body["error"] == f"robots.txt disallows {BLOCKED_URL}"
    assert browser.calls == []


def test_a_browser_task_with_an_allowed_url_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """a browser task with an allowed url proceeds to the browser and completes."""
    api, browser = _render(monkeypatch, ALLOWED_URL)

    assert api.named("fail") == [] and browser.calls == [ALLOWED_URL]
    assert len(api.named("complete")) == 1
