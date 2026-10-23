"""Polite HTTP GET for discovery task target URLs."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from discovery_ingest.config import DEFAULT_BOT_CONTACT_URL, build_user_agent
from discovery_ingest.worker.addresses import HostResolver, SystemResolver, validate_destination
from discovery_ingest.worker.outcome import FetchAbort, FetchFailure, FetchOutcome, classified, failure_outcome
from discovery_ingest.worker.pacing import HostPacer
from discovery_ingest.worker.redirects import MAX_REDIRECTS, REDIRECT_STATUSES, next_url
from discovery_ingest.worker.reply import Reply, read_reply
from discovery_ingest.worker.robots import RobotsCache, RobotsUnavailableError

Guard = Callable[[str], None]
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

__all__ = ["MAX_REDIRECTS", "FetchOutcome", "PoliteUrlFetcher"]


def _reply_outcome(reply: Reply, *, final_url: str, redirect_count: int) -> FetchOutcome:
    body = reply.body
    return FetchOutcome(
        http_status=reply.status_code,
        content_type=reply.headers.get("content-type"),
        byte_length=len(body),
        error_message=None,
        body=body if 200 <= reply.status_code < 300 else None,
        final_url=final_url,
        redirect_count=redirect_count,
    )


def _transport_failure(err: httpx.HTTPError) -> FetchFailure:
    return FetchFailure.TIMEOUT if isinstance(err, httpx.TimeoutException) else FetchFailure.CONNECTION


class PoliteUrlFetcher:
    """GET with timeout, per-host minimum interval, and validated redirect following."""

    def __init__(
        self,
        *,
        timeout_s: float = 30.0,
        min_interval_per_host_s: float = 1.0,
        http_client: httpx.Client | None = None,
        user_agent: str = build_user_agent(DEFAULT_BOT_CONTACT_URL),
        max_bytes: int = DEFAULT_MAX_BYTES,
        resolver: HostResolver | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._resolver: HostResolver = resolver or SystemResolver()
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._pacer = HostPacer(min_interval_per_host_s)
        self._http_client = http_client
        self._robots = RobotsCache(lambda robots_url: self._settle(robots_url, self._validate_hop))

    def get(self, url: str) -> FetchOutcome:
        """Perform a polite GET on ``url`` and return status and body metadata."""
        return self._settle(url, self._check_page)

    def _settle(self, url: str, guard: Guard) -> FetchOutcome:
        return classified(self._attempt(url, guard))

    def _attempt(self, url: str, guard: Guard) -> FetchOutcome:
        try:
            return self._follow(url, guard)
        except FetchAbort as abort:
            return abort.outcome()
        except httpx.HTTPError as err:
            return failure_outcome(str(err), _transport_failure(err))

    def _validate_hop(self, url: str) -> None:
        validate_destination(url, self._resolver)

    def _check_page(self, url: str) -> None:
        self._validate_hop(url)
        self._require_robots(url)

    def _require_robots(self, url: str) -> None:
        try:
            allowed = self._robots.allowed(url)
        except RobotsUnavailableError as err:
            raise FetchAbort(str(err), FetchFailure.ROBOTS_UNAVAILABLE) from err
        if not allowed:
            raise FetchAbort(f"robots.txt disallows {url}", FetchFailure.ROBOTS_DISALLOWED)

    def _follow(self, url: str, guard: Guard) -> FetchOutcome:
        current, seen = url, {url}
        for redirect_count in range(MAX_REDIRECTS + 1):
            guard(current)
            reply = self._visit(current)
            if reply.status_code not in REDIRECT_STATUSES:
                return _reply_outcome(reply, final_url=current, redirect_count=redirect_count)
            current = next_url(current, reply, seen)
        raise FetchAbort(f"too many redirects (limit {MAX_REDIRECTS})", FetchFailure.REDIRECT)

    def _visit(self, url: str) -> Reply:
        self._pacer.wait(urlparse(url).netloc or url)
        return self._request(url)

    def _request(self, url: str) -> Reply:
        if self._http_client is not None:
            return self._stream(self._http_client, url)
        with httpx.Client(trust_env=True, timeout=self._timeout_s) as client:
            return self._stream(client, url)

    def _stream(self, client: httpx.Client, url: str) -> Reply:
        headers = {"User-Agent": self._user_agent}
        with client.stream("GET", url, headers=headers, timeout=self._timeout_s) as response:
            return read_reply(response, max_bytes=self._max_bytes)
