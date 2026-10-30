"""Build the machine API client from the two settings the curation commands need."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.config import load_ingest_settings


def machine_client() -> DiscoveryMachineClient:
    """Return a client for ``DISCOVERY_API_URL`` with ``DISCOVERY_API_KEY``; no Cloudflare or storage setting is read."""
    settings = load_ingest_settings()
    return DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
