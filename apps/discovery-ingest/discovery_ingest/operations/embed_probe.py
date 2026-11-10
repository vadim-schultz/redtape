"""``embed probe``: run the embedding probe over real HTTP and render the report with the credentials scrubbed."""

from __future__ import annotations

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.embedding.client import CloudflareEmbeddingClient
from discovery_ingest.extract.embedding.probe import run_embed_probe
from discovery_ingest.extract.llm.redaction import scrub, secrets_of
from discovery_ingest.llm_settings import LlmSettings
from discovery_ingest.operations.probes import ProbeOutcome

EMBED_MIN_INTERVAL_SECONDS = 0.2


def embed_probe(settings: LlmSettings, *, model: str) -> ProbeOutcome:
    """Probe ``model`` and return the report as one JSON text; the outcome fails when the probe stopped early."""
    throttle = Throttle(EMBED_MIN_INTERVAL_SECONDS)
    with httpx.Client(trust_env=True) as http:
        client = CloudflareEmbeddingClient(settings, model=model, http=http, throttle=throttle)
        report = run_embed_probe(client, model)
    return ProbeOutcome([scrub(report.model_dump_json(indent=2), secrets_of(settings))], report.stopped is not None)
