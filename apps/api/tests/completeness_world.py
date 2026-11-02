"""Builders for the completeness read-model tests: procedures, candidates, mentions, edges, artifacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from app.features.discovery.repository.candidate_completeness import (
    CandidateCompleteness,
    completeness_columns,
    completeness_subquery,
)
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateEdge,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
    DiscoveryMentionRole,
    DiscoverySource,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _jurisdiction


class Row(NamedTuple):
    """One mention of a fixture: procedure index, codes per axis, the extractor, and any direct confidence.

    ``domain_confidence``/``situation_confidence`` stay ``None`` for an LLM-extracted assertion (the default,
    scored via the LLM-evidence curve); a non-``None`` value simulates a direct source (PVOG, a future vote).
    ``leaf_code`` simulates the PVOG leaf code a direct-confidence mention stashes (chapter 3).
    """

    procedure: int
    domains: list[str] | None = None
    situations: list[str] | None = None
    extractor: str = "llm"
    domain_confidence: float | None = None
    situation_confidence: float | None = None
    leaf_code: str | None = None


def procedures(session: Session, count: int) -> list[CatalogueService]:
    """Add ``count`` catalogue procedures of one jurisdiction."""
    jurisdiction = _jurisdiction(session)
    rows = [
        CatalogueService(
            source=DiscoverySource.GOVDATA,
            external_id=f"svc-{index}-{uuid.uuid4().hex[:8]}",
            jurisdiction_id=jurisdiction.id,
            title_i18n={"de": "Leistung"},
            raw_payload={},
            pipeline_stage="T0",
        )
        for index in range(count)
    ]
    session.add_all(rows)
    session.flush()
    return rows


def candidate(session: Session, procedure: CatalogueService, key: str) -> DiscoveryDocumentCandidate:
    """Add a staged candidate in the jurisdiction of ``procedure``."""
    row = DiscoveryDocumentCandidate(jurisdiction_id=procedure.jurisdiction_id, key=key, title_i18n={"de": key})
    session.add(row)
    session.flush()
    return row


def mention(session: Session, owner: DiscoveryDocumentCandidate, procedure: CatalogueService, row: Row) -> None:
    """Add one mention of ``owner`` in ``procedure`` carrying the codes and extractor of ``row``."""
    session.add(
        DiscoveryCandidateMention(
            candidate_id=owner.id,
            catalogue_service_id=procedure.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte mitbringen",
            source_field=f"details[{uuid.uuid4().hex[:8]}]",
            extractor=row.extractor,
            extractor_version="1",
            domain_codes=row.domains,
            situation_codes=row.situations,
            direct_domain_confidence=row.domain_confidence,
            direct_situation_confidence=row.situation_confidence,
            pvog_leaf_code=row.leaf_code,
        )
    )
    session.flush()


def mentioned(
    session: Session, owner: DiscoveryDocumentCandidate, procs: list[CatalogueService], rows: list[Row]
) -> None:
    """Add every mention of ``rows`` for ``owner``, resolving the procedure index."""
    for row in rows:
        mention(session, owner, procs[row.procedure], row)


def edge(session: Session, parent: DiscoveryDocumentCandidate, required: DiscoveryDocumentCandidate) -> None:
    """Add an edge ``parent requires required`` stated by a fresh procedure."""
    stated_in = procedures(session, 1)[0]
    session.add(
        DiscoveryCandidateEdge(
            parent_candidate_id=parent.id,
            required_candidate_id=required.id,
            catalogue_service_id=stated_in.id,
            excerpt="Personalausweis",
            basis=DiscoveryEdgeBasis.EXPLICIT,
            extractor="llm",
            extractor_version="1",
        )
    )
    session.flush()


def artifact(session: Session, procedure: CatalogueService, kind: DiscoveryArtifactKind) -> None:
    """Add a stored artifact of ``kind`` on ``procedure``."""
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    session.add(
        DiscoveryArtifact(
            catalogue_service_id=procedure.id,
            kind=kind,
            storage_key=f"discovery/{procedure.id}/{kind.value}/{sha}",
            sha256=sha,
            content_type="text/html",
            byte_size=10,
            source_url="https://example.gov/page",
            fetched_at=datetime(2026, 10, 26, 12, 0, tzinfo=UTC),
        )
    )
    session.flush()


def flags_of(session: Session) -> dict[uuid.UUID, CandidateCompleteness]:
    """Run the completeness subquery and return its rows by candidate id."""
    sub = completeness_subquery()
    rows = session.execute(select(*completeness_columns(sub))).all()
    return {row.candidate_id: CandidateCompleteness.from_row(row) for row in rows}
