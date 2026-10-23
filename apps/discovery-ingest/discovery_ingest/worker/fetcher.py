"""Polite HTTP GET for discovery task target URLs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

MAX_REDIRECTS = 5
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    """Result of one polite GET attempt."""

    http_status: int | None
    content_type: str | None
    byte_length: int | None
    error_message: str | None
    body: bytes | None = None
    final_url: str | None = None
    redirect_count: int = 0


class _FetchAbort(Exception):
    """A fetch that must stop with a failure outcome."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status

    def outcome(self) -> FetchOutcome:
        """Return the failure outcome this abort stands for."""
        return _failure(self.message, http_status=self.http_status)


def _failure(message: str, *, http_status: int | None = None) -> FetchOutcome:
    return FetchOutcome(
        http_status=http_status,
        content_type=None,
        byte_length=None,
        error_message=message,
        body=None,
    )


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


def _next_url(current: str, response: httpx.Response, seen: set[str]) -> str:
    """Resolve the redirect target of ``response`` or abort when it is unusable."""
    location = response.headers.get("location")
    if not location:
        raise _FetchAbort(f"HTTP {response.status_code} without Location header", http_status=response.status_code)
    target = str(urldefrag(urljoin(current, location)).url)
    if target in seen:
        raise _FetchAbort(f"redirect loop at {target}", http_status=response.status_code)
    seen.add(target)
    return target


class PoliteUrlFetcher:
    """GET with timeout, per-host minimum interval, and validated redirect following."""

    def __init__(
        self,
        *,
        timeout_s: float = 30.0,
        min_interval_per_host_s: float = 1.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._min_interval_s = min_interval_per_host_s
        self._http_client = http_client
        self._last_fetch_by_host: dict[str, float] = {}

    def get(self, url: str) -> FetchOutcome:
        """Perform a polite GET on ``url`` and return status and body metadata."""
        try:
            return self._follow(url)
        except _FetchAbort as abort:
            return abort.outcome()
        except httpx.HTTPError as err:
            return _failure(str(err))

    def _follow(self, url: str) -> FetchOutcome:
        current, seen = url, {url}
        for redirect_count in range(MAX_REDIRECTS + 1):
            response = self._visit(current)
            if response.status_code not in _REDIRECT_STATUSES:
                return _success(response, final_url=current, redirect_count=redirect_count)
            current = _next_url(current, response, seen)
        raise _FetchAbort(f"too many redirects (limit {MAX_REDIRECTS})")

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
            return self._http_client.get(url, timeout=self._timeout_s)
        with httpx.Client(trust_env=True, timeout=self._timeout_s) as client:
            return client.get(url)
