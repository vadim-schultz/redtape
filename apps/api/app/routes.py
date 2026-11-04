"""The app's only ungrouped route: the uptime health check."""

from __future__ import annotations

from litestar import get


@get("/health", sync_to_thread=False)
def health() -> dict[str, str]:
    """Report that the process is up; no DB or dependency check."""
    return {"status": "ok"}
