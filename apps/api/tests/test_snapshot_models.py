"""Snapshot translation models (chapter 07): the index row per page and locale, and the snapshot task queue."""

from __future__ import annotations

import uuid

import pytest
from app.models.discovery import CatalogueService, DiscoverySource
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from sqlalchemy.exc import DBAPIError, IntegrityError, StatementError
from sqlalchemy.orm import Session

HASH = "a" * 64
CONTENT_HASH = "b" * 64


def catalogue_row(session: Session) -> CatalogueService:
    """Add a catalogue row under a new jurisdiction and return it; every call makes a distinct page."""
    jurisdiction = Jurisdiction(kind=JurisdictionKind.COUNTRY, code=f"S{uuid.uuid4().hex[:8]}")
    session.add(jurisdiction)
    session.flush()
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=uuid.uuid4().hex,
        jurisdiction_id=jurisdiction.id,
        title_i18n={"de": "Leistung"},
        raw_payload={},
        pipeline_stage="T0",
    )
    session.add(row)
    session.flush()
    return row


def _index_row(catalogue: CatalogueService, locale: str = "en") -> SnapshotTranslation:
    return SnapshotTranslation(
        catalogue_service_id=catalogue.id,
        locale=locale,
        artifact_sha256=HASH,
        source_hash=HASH,
        engine="azure-translator",
        model=None,
        storage_key=f"translations/v1/snapshots/{catalogue.id}/{locale}/{CONTENT_HASH}.json",
        content_sha256=CONTENT_HASH,
        size_bytes=212,
    )


def _task(catalogue: CatalogueService, status: WorkTaskStatus = WorkTaskStatus.PENDING) -> SnapshotTranslationTask:
    return SnapshotTranslationTask(catalogue_service_id=catalogue.id, locale="en", source_hash=HASH, status=status)


def test_an_index_row_is_found_by_page_and_locale_and_carries_its_provenance(db_session: Session) -> None:
    """model · an index row is found by (catalogue row, locale) and carries the hashes, engine and object key."""
    catalogue = catalogue_row(db_session)
    db_session.add_all([_index_row(catalogue, "en"), _index_row(catalogue, "tr")])
    db_session.flush()

    row = db_session.get(SnapshotTranslation, (catalogue.id, "tr"))

    assert row is not None
    assert (row.artifact_sha256, row.source_hash, row.engine, row.content_sha256) == (
        HASH,
        HASH,
        "azure-translator",
        CONTENT_HASH,
    )
    assert (row.truncated, row.skipped_reason, row.size_bytes) == (False, None, 212)
    assert row.created_at is not None and row.updated_at is not None


def test_a_skipped_page_stores_a_reason_and_no_object_key(db_session: Session) -> None:
    """model · a page skipped with a reason is stored with that reason and without a storage key."""
    catalogue = catalogue_row(db_session)
    skipped = _index_row(catalogue)
    skipped.storage_key = None
    skipped.content_sha256 = None
    skipped.size_bytes = None
    skipped.skipped_reason = "too_short"
    db_session.add(skipped)
    db_session.flush()
    db_session.expire(skipped)

    assert (skipped.storage_key, skipped.skipped_reason) == (None, "too_short")


def test_a_row_with_both_storage_key_and_skipped_reason_is_refused_by_the_check_constraint(db_session: Session) -> None:
    """model · a row with both storage_key and skipped_reason is refused by the check constraint."""
    catalogue = catalogue_row(db_session)
    row = _index_row(catalogue)
    row.skipped_reason = "too_short"
    db_session.add(row)

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("open_status", [WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED])
def test_a_second_open_task_for_the_same_catalogue_row_and_locale_is_refused(
    db_session: Session, open_status: WorkTaskStatus
) -> None:
    """model · a second open (pending or claimed) task for the same catalogue row and locale is refused."""
    catalogue = catalogue_row(db_session)
    db_session.add(_task(catalogue, open_status))
    db_session.flush()

    db_session.add(_task(catalogue))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_status_outside_the_work_task_status_enum_is_refused(db_session: Session) -> None:
    """model · a task status outside the work_task_status enum is refused instead of stored."""
    task = _task(catalogue_row(db_session))
    task.status = "robot"  # type: ignore[assignment]
    db_session.add(task)

    with pytest.raises((DBAPIError, StatementError, LookupError)):
        db_session.flush()
