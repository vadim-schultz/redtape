"""``artifacts list`` and ``artifacts download``: bring stored page snapshots to a developer as fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

from discovery_ingest.artifacts import ArtifactKind, ArtifactQuery, ArtifactRead
from discovery_ingest.client import DiscoveryIngestClient

MAX_PAGE_SIZE = 100
"""The most artifacts the route serves in one page."""


def artifact_pages(client: DiscoveryIngestClient, host: str, kind: ArtifactKind, limit: int) -> Iterator[ArtifactRead]:
    """Yield up to ``limit`` artifacts of ``host``, one route page at a time, newest first."""
    offset = 0
    while offset < limit:
        page = client.artifacts.list(
            ArtifactQuery(host=host, kind=kind, offset=offset, limit=min(MAX_PAGE_SIZE, limit - offset))
        )
        yield from page.items
        offset += len(page.items)
        if not page.items or offset >= page.total:
            return


def write_artifact(client: DiscoveryIngestClient, artifact_id: UUID, out: Path) -> int:
    """Write the stored bytes of one artifact to ``out``, creating parent directories; return the byte count."""
    content = client.artifacts.content(artifact_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content.data)
    return len(content.data)
