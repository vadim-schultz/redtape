"""Redirect handling for the polite fetcher."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin

import httpx

from discovery_ingest.worker.outcome import FetchAbort

MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def next_url(current: str, response: httpx.Response, seen: set[str]) -> str:
    """Resolve the redirect target of ``response`` or abort when it is unusable."""
    location = response.headers.get("location")
    if not location:
        raise FetchAbort(f"HTTP {response.status_code} without Location header", http_status=response.status_code)
    target = str(urldefrag(urljoin(current, location)).url)
    if target in seen:
        raise FetchAbort(f"redirect loop at {target}", http_status=response.status_code)
    seen.add(target)
    return target
