"""Procedures of a candidate and the cleaned text of their stored pages: what the curator reads and the check compares."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.artifacts import ArtifactQuery, ArtifactRead
from discovery_ingest.candidate_sources import CandidateSourceRead, SourceQuery
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.decode import decode_html

PAGE_SIZE = 100
"""The most the list routes serve in one page."""


def candidate_procedures(client: DiscoveryIngestClient, candidate_id: UUID) -> list[CandidateSourceRead]:
    """Return every procedure that mentions the candidate."""
    found: list[CandidateSourceRead] = []
    while True:
        page = client.candidates.list_sources(
            SourceQuery(
                host=None, missing=None, candidate_id=candidate_id, service_ids=[], offset=len(found), limit=PAGE_SIZE
            )
        )
        found += page.items
        if not page.items or len(found) >= page.total:
            return found


def newest_snapshot(client: DiscoveryIngestClient, source: CandidateSourceRead) -> ArtifactRead | None:
    """Return the newest html snapshot of the procedure, searching its host's snapshots newest first."""
    offset = 0
    while True:
        page = client.artifacts.list(
            ArtifactQuery(host=source.host, kind="html_snapshot", offset=offset, limit=PAGE_SIZE)
        )
        for artifact in page.items:
            if artifact.catalogue_service_id == source.catalogue_service_id:
                return artifact
        offset += len(page.items)
        if not page.items or offset >= page.total:
            return None


def cleaned_text(client: DiscoveryIngestClient, source: CandidateSourceRead) -> str | None:
    """Return the cleaned text of the procedure's newest snapshot, or ``None`` when none is stored."""
    snapshot = newest_snapshot(client, source)
    if snapshot is None:
        return None
    content = client.artifacts.content(snapshot.id)
    return clean_page(decode_html(content.data, content.content_type), source.source_url).text


class PageTexts:
    """Cleaned page text per procedure, fetched at most once however many excerpts are checked against it."""

    def __init__(self, client: DiscoveryIngestClient) -> None:
        """Keep the client that fetches the pages."""
        self._client = client
        self._texts: dict[UUID, str | None] = {}

    def __call__(self, source: CandidateSourceRead) -> str | None:
        """Return the cleaned text of ``source``'s newest snapshot, or ``None`` when none is stored."""
        if source.catalogue_service_id not in self._texts:
            self._texts[source.catalogue_service_id] = cleaned_text(self._client, source)
        return self._texts[source.catalogue_service_id]
