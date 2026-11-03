"""The artifact storage check shared by the drains that read or write stored snapshots."""

from __future__ import annotations

import httpx
from pydantic import ValidationError

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError


def storage_problem(client: DiscoveryIngestClient, consequence: str) -> str | None:
    """Return why artifact storage is not ready (``consequence`` says what that breaks), or ``None`` when it is."""
    try:
        enabled = client.artifacts.status().storage_enabled
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
        return f"cannot read the artifact storage status: {err}"
    return None if enabled else f"artifact storage is not configured on the API; {consequence}"
