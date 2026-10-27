"""The one table of Browser Run quick-action paths; nothing else builds an endpoint URL."""

from __future__ import annotations

from typing import Literal

Endpoint = Literal["content", "snapshot", "screenshot"]
API_BASE = "https://api.cloudflare.com/client/v4/accounts"
ENDPOINT_PATHS: dict[Endpoint, str] = {
    "content": "browser-run/content",
    "snapshot": "browser-run/snapshot",
    "screenshot": "browser-run/screenshot",
}


def endpoint_url(account_id: str, endpoint: Endpoint) -> str:
    """Return the REST URL of ``endpoint`` for ``account_id``."""
    return f"{API_BASE}/{account_id}/{ENDPOINT_PATHS[endpoint]}"
