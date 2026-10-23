"""Polite HTTP GET for discovery task target URLs."""

from __future__ import annotations

import time
from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from discovery_ingest.config import DEFAULT_BOT_CONTACT_URL, build_user_agent
from discovery_ingest.worker.outcome import FetchAbort, FetchOutcome, failure_outcome
from discovery_ingest.worker.redirects import MAX_REDIRECTS, REDIRECT_STATUSES, next_url
from discovery_ingest.worker.robots import RobotsCache, RobotsUnavailableError

Guard = Callable[[str], None]

__all__ = ["MAX_REDIRECTS", "FetchOutcome", "PoliteUrlFetcher"]


def _success(response: httpx.Response, *, final_url: str, redirect_count: int) -> FetchOutcome:
    body = response.content
    return FetchOutcome(
        http_status=response.status_code,
        content_type=response.headers.get("content-type"),
        byte_length=len(body),
        error_message=None,
        body=body if response.status_code < 400 else None,
        final_url=final_url,
        redirect_count=redirect_count,
    )


def _unguarded(url: str) -> None:
    """Guard for requests that need no pre-flight check."""


class PoliteUrlFetcher:
    """GET with timeout, per-host minimum interval, and validated redirect following."""

    def __init__(
        self,
        *,
        timeout_s: float = 30.0,
        min_interval_per_host_s: float = 1.0,
        http_client: httpx.Client | None = None,
        user_agent: str = build_user_agent(DEFAULT_BOT_CONTACT_URL),
    ) -> None:
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._min_interval_s = min_interval_per_host_s
        self._http_client = http_client
        self._last_fetch_by_host: dict[str, float] = {}
        self._robots = RobotsCache(lambda robots_url: self._settle(robots_url, _unguarded))

    def get(self, url: str) -> FetchOutcome:
        """Perform a polite GET on ``url`` and return status and body metadata."""
        return self._settle(url, self._require_robots)

    def _settle(self, url: str, guard: Guard) -> FetchOutcome:
        try:
            return self._follow(url, guard)
        except FetchAbort as abort:
            return abort.outcome()
        except httpx.HTTPError as err:
            return failure_outcome(str(err))

    def _require_robots(self, url: str) -> None:
        try:
            allowed = self._robots.allowed(url)
        except RobotsUnavailableError as err:
            raise FetchAbort(str(err)) from err
        if not allowed:
            raise FetchAbort(f"robots.txt disallows {url}")

    def _follow(self, url: str, guard: Guard) -> FetchOutcome:
        current, seen = url, {url}
        for redirect_count in range(MAX_REDIRECTS + 1):
            guard(current)
            response = self._visit(current)
            if response.status_code not in REDIRECT_STATUSES:
                return _success(response, final_url=current, redirect_count=redirect_count)
            current = next_url(current, response, seen)
        raise FetchAbort(f"too many redirects (limit {MAX_REDIRECTS})")

    def _visit(self, url: str) -> httpx.Response:
        self._wait_for_host(urlparse(url).netloc or url)
        return self._request(url)

    def _wait_for_host(self, host: str) -> None:
        now = time.monotonic()
        last = self._last_fetch_by_host.get(host, 0.0)
        elapsed = now - last
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_fetch_by_host[host] = time.monotonic()

    def _request(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url, headers=self._headers, timeout=self._timeout_s)
        with httpx.Client(trust_env=True, timeout=self._timeout_s, headers=self._headers) as client:
            return client.get(url)

    @property
    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._user_agent}
