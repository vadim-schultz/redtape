"""``candidates page --out``: write the cleaned text of each procedure's snapshot to a directory."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.curation_pages import cleaned_text


def write_cleaned_texts(client: DiscoveryIngestClient, sources: list[CandidateSourceRead], out: Path) -> list[UUID]:
    """Write ``<catalogue_service_id>.txt`` for each procedure with a snapshot; return the ids that have none."""
    missing: list[UUID] = []
    for source in sources:
        text = cleaned_text(client, source)
        if text is None:
            missing.append(source.catalogue_service_id)
            continue
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{source.catalogue_service_id}.txt").write_text(text, encoding="utf-8")
    return missing
