"""Polite HTTP GET for discovery task target URLs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    """Result of one polite GET attempt."""

    http_status: int | None
    content_type: str | None
    byte_length: int | None
    error_message: str | None
    body: bytes | None = None


class PoliteUrlFetcher:
    """GET with timeout and per-host minimum interval between requests."""

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
        host = urlparse(url).netloc or url
        self._wait_for_host(host)
        try:
            response = self._request(url)
        except httpx.TimeoutException as err:
            return FetchOutcome(
                http_status=None,
                content_type=None,
                byte_length=None,
                error_message=str(err),
                body=None,
            )
        except httpx.HTTPError as err:
            return FetchOutcome(
                http_status=None,
                content_type=None,
                byte_length=None,
                error_message=str(err),
                body=None,
            )
        content_type = response.headers.get("content-type")
        body = response.content
        response_body = body if response.status_code < 400 else None
        return FetchOutcome(
            http_status=response.status_code,
            content_type=content_type,
            byte_length=len(body),
            error_message=None,
            body=response_body,
        )

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
