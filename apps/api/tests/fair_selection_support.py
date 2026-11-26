"""Builders for the fair-selection tests: each task row is written with the parent row its foreign key needs."""

from __future__ import annotations

import uuid

from app.config import settings
from app.models.discovery import CatalogueService, DiscoveryDocumentCandidate, DiscoveryTask
from app.models.discovery.enums import DiscoveryTaskKind, DiscoveryTaskStatus
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session

from search_support import make_candidate
from test_discovery_admin_api import _catalogue


def catalogue_page(session: Session) -> CatalogueService:
    """Add a procedure page with a unique external id and return it."""
    return _catalogue(session, external_id=f"svc-{uuid.uuid4().hex[:8]}")


def translation_task(
    session: Session,
    candidate: DiscoveryDocumentCandidate | None = None,
    *,
    locale: str = "de",
    status: WorkTaskStatus = WorkTaskStatus.PENDING,
    priority: int = 100,
    phase: int = 1,
) -> TranslationTask:
    """Add a translation task of ``candidate`` (a new candidate when omitted) and return it."""
    owner = make_candidate(session) if candidate is None else candidate
    task = TranslationTask(
        candidate_id=owner.id,
        locale=locale,
        source_hash="test-hash",
        status=status,
        priority=priority,
        phase=phase,
    )
    session.add(task)
    session.flush()
    return task


def embedding_task(
    session: Session,
    candidate: DiscoveryDocumentCandidate | None = None,
    *,
    locale: str = "de",
    status: WorkTaskStatus = WorkTaskStatus.PENDING,
    priority: int = 100,
    phase: int = 1,
) -> EmbeddingTask:
    """Add an embedding task of ``candidate`` (a new candidate when omitted) and return it."""
    owner = make_candidate(session) if candidate is None else candidate
    task = EmbeddingTask(
        candidate_id=owner.id,
        model=settings.embedding_model,
        locale=locale,
        text_hash="test-hash",
        status=status,
        priority=priority,
        phase=phase,
    )
    session.add(task)
    session.flush()
    return task


def snapshot_task(
    session: Session,
    page: CatalogueService | None = None,
    *,
    locale: str = "de",
    status: WorkTaskStatus = WorkTaskStatus.PENDING,
    priority: int = 100,
    phase: int = 1,
) -> SnapshotTranslationTask:
    """Add a snapshot translation task of ``page`` (a new page when omitted) and return it."""
    owner = catalogue_page(session) if page is None else page
    task = SnapshotTranslationTask(
        catalogue_service_id=owner.id,
        locale=locale,
        source_hash="test-hash",
        status=status,
        priority=priority,
        phase=phase,
    )
    session.add(task)
    session.flush()
    return task


def discovery_task(
    session: Session,
    page: CatalogueService | None = None,
    *,
    kind: DiscoveryTaskKind = DiscoveryTaskKind.FETCH_URL,
    status: DiscoveryTaskStatus = DiscoveryTaskStatus.PENDING,
    priority: int = 100,
    phase: int = 1,
) -> DiscoveryTask:
    """Add a discovery task of ``page`` (a new page when omitted) and return it."""
    owner = catalogue_page(session) if page is None else page
    task = DiscoveryTask(
        catalogue_service_id=owner.id,
        kind=kind,
        target_url="https://example.gov/leistung",
        status=status,
        priority=priority,
        phase=phase,
    )
    session.add(task)
    session.flush()
    return task


def candidate_ids(session: Session, count: int) -> list[uuid.UUID]:
    """Add ``count`` candidates and return their ids, for rows that reference a candidate."""
    return [make_candidate(session).id for _ in range(count)]
