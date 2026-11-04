"""Build the Workers AI client that every model-calling flow shares."""

from __future__ import annotations

from contextlib import ExitStack

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.config import IngestSettings
from discovery_ingest.extract.llm.cloudflare import DEFAULT_MIN_INTERVAL_SECONDS, CloudflareAiClient


def build_model_client(settings: IngestSettings, model: str, stack: ExitStack) -> CloudflareAiClient:
    """Return a Workers AI client for ``model`` with its throttle; its HTTP client is entered into ``stack``.

    The owner closes ``stack`` on every exit path. Raises :class:`ValueError` when the credentials are missing.
    """
    http = stack.enter_context(httpx.Client(trust_env=True))
    return CloudflareAiClient(settings, model=model, http=http, throttle=Throttle(DEFAULT_MIN_INTERVAL_SECONDS))
