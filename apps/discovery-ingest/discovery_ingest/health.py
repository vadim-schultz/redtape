"""Retry Render API health checks before scheduled ingest."""

from __future__ import annotations

import time

import httpx


class ApiHealthError(RuntimeError):
    """API did not become healthy within the retry budget."""


def wait_for_api(
    base_url: str,
    *,
    max_attempts: int = 12,
    retry_delay_seconds: float = 10.0,
    http_client: httpx.Client | None = None,
) -> None:
    """Poll ``GET {base_url}/health`` until HTTP 200 or attempts are exhausted."""
    health_url = f"{base_url.rstrip('/')}/health"
    last_status: int | None = None

    for attempt in range(1, max_attempts + 1):
        status = _probe_health(health_url, http_client=http_client)
        if status == 200:
            return
        last_status = status
        if attempt < max_attempts and retry_delay_seconds > 0:
            time.sleep(retry_delay_seconds)

    raise ApiHealthError(
        f"API health check failed after {max_attempts} attempts (last status {last_status})",
    )


def _probe_health(url: str, *, http_client: httpx.Client | None) -> int:
    if http_client is not None:
        response = http_client.get(url)
    else:
        with httpx.Client(trust_env=True, timeout=30.0) as client:
            response = client.get(url)
    return response.status_code
