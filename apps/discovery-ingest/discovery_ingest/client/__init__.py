"""Client for the discovery machine API: one facade, one resource class per API area."""

from discovery_ingest.client.errors import DiscoveryMachineApiError
from discovery_ingest.client.ingest_client import DiscoveryIngestClient

__all__ = ["DiscoveryIngestClient", "DiscoveryMachineApiError"]
