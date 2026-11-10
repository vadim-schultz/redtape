"""Builders shared by the search-text tests: a candidate with mentions on a real database."""

from __future__ import annotations

import uuid

from app.config import settings
from app.features.search.service import SearchTextService
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from app.models.search import CandidateEmbedding, EmbeddingTask
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue


def make_candidate(session: Session, title: str = "Kindergeldantrag") -> DiscoveryDocumentCandidate:
    """Add a candidate titled ``title`` in a fresh jurisdiction."""
    catalogue = _catalogue(session, external_id=f"svc-{uuid.uuid4().hex[:8]}")
    row = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=uuid.uuid4().hex, title_i18n={"de": title} if title else {}
    )
    session.add(row)
    session.flush()
    return row


def make_mention(
    session: Session, candidate: DiscoveryDocumentCandidate, excerpt: str, score: float | None = None
) -> DiscoveryCandidateMention:
    """Add a mention of ``candidate`` with ``excerpt`` and a direct category confidence of ``score``."""
    catalogue = session.scalars(select(CatalogueService)).first()
    assert catalogue is not None
    mention = DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=catalogue.id,
        role=DiscoveryMentionRole.REQUIRED,
        excerpt=excerpt,
        source_field=f"details[{uuid.uuid4().hex[:6]}]",
        extractor="test",
        extractor_version="1",
        direct_category_confidence=score,
    )
    session.add(mention)
    session.flush()
    return mention


def search_service(session: Session) -> SearchTextService:
    """Return the service as the hooks build it."""
    return SearchTextService.for_session(session)


def open_tasks(session: Session) -> list[EmbeddingTask]:
    """Return every embedding task, oldest first."""
    return list(session.scalars(select(EmbeddingTask).order_by(EmbeddingTask.created_at, EmbeddingTask.id)))


def embed(session: Session, candidate: DiscoveryDocumentCandidate, text_hash: str) -> None:
    """Store an embedding of ``candidate`` for the configured model at ``text_hash``."""
    session.add(
        CandidateEmbedding(
            candidate_id=candidate.id,
            model=settings.embedding_model,
            locale="de",
            dim=settings.embedding_dim,
            text_hash=text_hash,
            embedding=[0.0] * settings.embedding_dim,
        )
    )
    session.flush()
