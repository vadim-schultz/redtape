"""The one table of Workers AI paths; nothing else builds an endpoint URL."""

from __future__ import annotations

from typing import Literal

Endpoint = Literal["run", "chat", "tomarkdown"]
API_BASE = "https://api.cloudflare.com/client/v4/accounts"
ENDPOINT_PATHS: dict[Endpoint, str] = {
    "run": "ai/run/{model}",
    "chat": "ai/v1/chat/completions",
    "tomarkdown": "ai/tomarkdown",
}


def endpoint_url(account_id: str, endpoint: Endpoint, model: str = "") -> str:
    """Return the REST URL of ``endpoint`` for ``account_id`` (``model`` fills the ``run`` path)."""
    return f"{API_BASE}/{account_id}/{ENDPOINT_PATHS[endpoint].format(model=model)}"
