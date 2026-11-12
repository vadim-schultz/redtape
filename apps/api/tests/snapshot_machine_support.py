"""Builders shared by the snapshot machine tests (chapter 08): pages, snapshots, index rows and task rows."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Final, NamedTuple

from app.features.translation.task_repository import TaskRepository
from app.models.discovery import CatalogueService, DiscoveryArtifact, DiscoveryArtifactKind
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from sqlalchemy import select
from sqlalchemy.orm import Session

from embedding_support import NOW
from test_snapshot_models import catalogue_row

SHA_OLD: Final = "1" * 64
SHA_A: Final = "a" * 64
SHA_B: Final = "b" * 64
HASH_STORED: Final = "c" * 64
HASH_NEW: Final = "d" * 64
CONTENT: Final = "e" * 64
SOURCE_URL: Final = "https://www.example.de/leistung/kindergeld"


class Page(NamedTuple):
    """A procedure page with its snapshot and the open task queued for one locale."""

    catalogue: CatalogueService
    artifact: DiscoveryArtifact
    task: SnapshotTranslationTask


def add_snapshot(
    session: Session,
    catalogue: CatalogueService,
    sha: str = SHA_A,
    fetched_at: datetime = NOW - timedelta(days=1),
) -> DiscoveryArtifact:
    """Add an HTML snapshot of ``catalogue`` whose bytes hash to ``sha``, fetched at ``fetched_at``."""
    artifact = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryArtifactKind.HTML_SNAPSHOT,
        storage_key=f"artifacts/{sha}.html",
        sha256=sha,
        content_type="text/html",
        byte_size=2048,
        source_url=SOURCE_URL,
        final_url=None,
        fetched_at=fetched_at,
    )
    session.add(artifact)
    session.flush()
    return artifact


def queue_page(session: Session, locale: str = "en") -> Page:
    """Add a procedure page with one snapshot and queue its translation into ``locale`` through the upsert."""
    catalogue = catalogue_row(session)
    artifact = add_snapshot(session, catalogue)
    TaskRepository(session).upsert_snapshot_pending((catalogue.id, locale), SHA_A, 100)
    (task,) = [row for row in task_rows(session, catalogue.id, locale) if row.status is WorkTaskStatus.PENDING]
    return Page(catalogue, artifact, task)


def task_rows(session: Session, catalogue_id: uuid.UUID, locale: str = "en") -> list[SnapshotTranslationTask]:
    """Return every snapshot task of one page and locale, oldest first, read fresh from the database."""
    session.flush()
    stmt = (
        select(SnapshotTranslationTask)
        .where(
            SnapshotTranslationTask.catalogue_service_id == catalogue_id,
            SnapshotTranslationTask.locale == locale,
        )
        .order_by(SnapshotTranslationTask.created_at, SnapshotTranslationTask.id)
        .execution_options(populate_existing=True)
    )
    return list(session.scalars(stmt))


def index_row(session: Session, catalogue_id: uuid.UUID, locale: str = "en") -> SnapshotTranslation | None:
    """Return the index row of one page and locale, read fresh from the database, or ``None``."""
    session.flush()
    return session.get(SnapshotTranslation, (catalogue_id, locale), populate_existing=True)


def stored_row(
    session: Session,
    catalogue: CatalogueService,
    locale: str = "en",
    *,
    source_hash: str = HASH_STORED,
    artifact_sha: str = SHA_OLD,
) -> SnapshotTranslation:
    """Add the index row of a stored translation of ``catalogue`` made from ``artifact_sha`` and ``source_hash``."""
    row = SnapshotTranslation(
        catalogue_service_id=catalogue.id,
        locale=locale,
        artifact_sha256=artifact_sha,
        source_hash=source_hash,
        engine="azure-translator",
        model=None,
        storage_key=f"translations/v1/snapshots/{catalogue.id}/{locale}/{CONTENT}.json",
        content_sha256=CONTENT,
        size_bytes=300,
        truncated=False,
        skipped_reason=None,
    )
    session.add(row)
    session.flush()
    return row


def skipped_row(
    session: Session, catalogue: CatalogueService, locale: str = "en", reason: str = "too_short"
) -> SnapshotTranslation:
    """Add the marker row of a page skipped with ``reason``; a marker has no object key."""
    row = SnapshotTranslation(
        catalogue_service_id=catalogue.id,
        locale=locale,
        artifact_sha256=SHA_A,
        source_hash=HASH_STORED,
        engine="none",
        model=None,
        storage_key=None,
        content_sha256=None,
        size_bytes=None,
        truncated=False,
        skipped_reason=reason,
    )
    session.add(row)
    session.flush()
    return row


def task_in_state(
    session: Session,
    catalogue: CatalogueService,
    status: WorkTaskStatus,
    locale: str = "en",
    source_hash: str = SHA_A,
) -> SnapshotTranslationTask:
    """Add a snapshot task of ``catalogue`` and ``locale`` in ``status``, queued against ``source_hash``."""
    task = SnapshotTranslationTask(
        catalogue_service_id=catalogue.id, locale=locale, source_hash=source_hash, priority=100, status=status
    )
    session.add(task)
    session.flush()
    return task
