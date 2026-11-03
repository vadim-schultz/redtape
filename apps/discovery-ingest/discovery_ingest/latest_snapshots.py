"""Select the newest stored html snapshot of each catalogue row from the machine artifacts list route."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

from discovery_ingest.artifacts import ArtifactQuery, ArtifactRead
from discovery_ingest.client import DiscoveryIngestClient

PAGE_SIZE = 100
"""The most the list route serves in one page."""


def _snapshots(client: DiscoveryIngestClient, host: str | None) -> Iterator[ArtifactRead]:
    """Yield every stored html snapshot, newest first, one route page at a time."""
    offset = 0
    while True:
        page = client.artifacts.list(ArtifactQuery(host=host, kind="html_snapshot", offset=offset, limit=PAGE_SIZE))
        yield from page.items
        offset += len(page.items)
        if not page.items or offset >= page.total:
            return


def latest_snapshots(client: DiscoveryIngestClient, host: str | None, limit: int) -> list[ArtifactRead]:
    """Return the newest snapshot of up to ``limit`` catalogue rows."""
    chosen: dict[UUID, ArtifactRead] = {}
    for artifact in _snapshots(client, host):
        chosen.setdefault(artifact.catalogue_service_id, artifact)
        if len(chosen) >= limit:
            break
    return list(chosen.values())
