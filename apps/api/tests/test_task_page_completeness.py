"""Page-level completeness (D6): catalogue_service_id-keyed chip count used only to order claims."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.features.discovery.repository.task_page_completeness import page_completeness_subquery
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateEdge,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
    DiscoveryMentionRole,
)
from sqlalchemy import Uuid, func, literal, select
from sqlalchemy.orm import Session

import completeness_world as world

SNAPSHOT, SCREENSHOT = DiscoveryArtifactKind.HTML_SNAPSHOT, DiscoveryArtifactKind.SCREENSHOT


def _owner(session: Session, procedure: CatalogueService) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(
        jurisdiction_id=procedure.jurisdiction_id, key=f"k-{uuid.uuid4().hex[:8]}", title_i18n={"de": "x"}
    )
    session.add(row)
    session.flush()
    return row


def _mention(
    session: Session,
    procedure: CatalogueService,
    owner: DiscoveryDocumentCandidate,
    *,
    domain: list[str] | None = None,
    situation: list[str] | None = None,
) -> None:
    session.add(
        DiscoveryCandidateMention(
            candidate_id=owner.id,
            catalogue_service_id=procedure.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte mitbringen",
            source_field=f"details[{uuid.uuid4().hex[:8]}]",
            extractor="llm",
            extractor_version="1",
            category_codes=[*domain, *situation],
        )
    )
    session.flush()


def _edge(
    session: Session,
    procedure: CatalogueService,
    parent: DiscoveryDocumentCandidate,
    required: DiscoveryDocumentCandidate,
) -> None:
    session.add(
        DiscoveryCandidateEdge(
            parent_candidate_id=parent.id,
            required_candidate_id=required.id,
            catalogue_service_id=procedure.id,
            excerpt="Personalausweis",
            basis=DiscoveryEdgeBasis.EXPLICIT,
            extractor="llm",
            extractor_version="1",
        )
    )
    session.flush()


def _artifact(session: Session, procedure: CatalogueService, kind: DiscoveryArtifactKind) -> None:
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


def _completeness_of(session: Session, catalogue_service_id: uuid.UUID) -> int:
    """Mirror the claim query's outer-join-and-coalesce: a page with no row here is ``0``, not missing."""
    sub = page_completeness_subquery()
    anchor = select(literal(catalogue_service_id, type_=Uuid(as_uuid=True)).label("catalogue_service_id")).subquery()
    stmt = (
        select(func.coalesce(sub.c.page_completeness, 0))
        .select_from(anchor)
        .outerjoin(sub, sub.c.catalogue_service_id == anchor.c.catalogue_service_id)
    )
    return session.scalar(stmt)


def test_a_page_with_every_signal_is_five_of_five(db_session: Session) -> None:
    procs = world.procedures(db_session, 1)
    page = procs[0]
    parent, required = _owner(db_session, page), _owner(db_session, page)
    _mention(db_session, page, parent, domain=["home-and-housing"], situation=["moving-house"])
    _edge(db_session, page, parent, required)
    _artifact(db_session, page, SNAPSHOT)
    _artifact(db_session, page, SCREENSHOT)

    assert _completeness_of(db_session, page.id) == 5


def test_a_page_with_only_some_signals_counts_only_those(db_session: Session) -> None:
    procs = world.procedures(db_session, 1)
    page = procs[0]
    owner = _owner(db_session, page)
    _mention(db_session, page, owner, domain=["home-and-housing"])
    _artifact(db_session, page, SNAPSHOT)

    assert _completeness_of(db_session, page.id) == 2


def test_a_page_with_nothing_coalesces_to_zero_and_chips_never_leak_to_another_page(db_session: Session) -> None:
    procs = world.procedures(db_session, 2)
    bare, busy = procs
    owner = _owner(db_session, busy)
    _mention(db_session, busy, owner, domain=["home-and-housing"], situation=["moving-house"])
    _edge(db_session, busy, owner, _owner(db_session, busy))
    _artifact(db_session, busy, SNAPSHOT)
    _artifact(db_session, busy, SCREENSHOT)

    assert _completeness_of(db_session, bare.id) == 0
    assert _completeness_of(db_session, busy.id) == 5
