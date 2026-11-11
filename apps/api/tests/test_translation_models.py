"""Translation schema (chapter 13): the index row per candidate and locale and the translation task queue."""

from __future__ import annotations

import uuid

import pytest
from app.models import ApiKey, Jurisdiction, JurisdictionKind
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError, IntegrityError, StatementError
from sqlalchemy.orm import Session

HASH = "a" * 64
CONTENT_HASH = "b" * 64


def _candidate(session: Session) -> DiscoveryDocumentCandidate:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(country)
    session.flush()
    row = DiscoveryDocumentCandidate(jurisdiction_id=country.id, key=uuid.uuid4().hex, title_i18n={"de": "Antrag"})
    session.add(row)
    session.flush()
    return row


def _translation(candidate: DiscoveryDocumentCandidate, locale: str = "en") -> CandidateTranslation:
    return CandidateTranslation(
        candidate_id=candidate.id,
        locale=locale,
        source_hash=HASH,
        engine="llm",
        model="@cf/qwen/qwen3-30b-a3b-fp8",
        storage_key=f"translations/v1/{candidate.id}/{locale}/card/{CONTENT_HASH}.json",
        content_sha256=CONTENT_HASH,
        size_bytes=212,
    )


def _task(candidate: DiscoveryDocumentCandidate, status: WorkTaskStatus = WorkTaskStatus.PENDING) -> TranslationTask:
    return TranslationTask(candidate_id=candidate.id, locale="en", source_hash=HASH, status=status)


def test_an_index_row_per_candidate_and_locale_is_found_by_key_and_carries_its_provenance(db_session: Session) -> None:
    """translation · an index row per candidate and locale is found by key and carries engine, model, hash and object key."""
    candidate = _candidate(db_session)
    db_session.add_all([_translation(candidate, "en"), _translation(candidate, "tr")])
    db_session.flush()

    row = db_session.get(CandidateTranslation, (candidate.id, "tr"))

    assert row is not None
    assert (row.engine, row.model, row.source_hash, row.content_sha256) == (
        "llm",
        "@cf/qwen/qwen3-30b-a3b-fp8",
        HASH,
        CONTENT_HASH,
    )
    assert row.storage_key == f"translations/v1/{candidate.id}/tr/card/{CONTENT_HASH}.json"
    assert (row.source, row.size_bytes) == (TranslationSource.MT, 212)
    assert row.created_at is not None and row.updated_at is not None


def test_a_duplicate_candidate_and_locale_is_refused(db_session: Session) -> None:
    """translation · a duplicate (candidate, locale) row is refused."""
    candidate = _candidate(db_session)
    db_session.add(_translation(candidate))
    db_session.flush()

    db_session.add(_translation(candidate))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_source_other_than_mt_or_human_is_refused(db_session: Session) -> None:
    """translation · the provenance is an enum: an unknown source is refused instead of stored."""
    candidate = _candidate(db_session)
    row = _translation(candidate)
    row.source = "robot"  # type: ignore[assignment]
    db_session.add(row)

    with pytest.raises((DBAPIError, StatementError, LookupError)):
        db_session.flush()


def test_a_human_row_keeps_its_provenance(db_session: Session) -> None:
    """translation · a human row is stored as human, so a machine write can be refused later."""
    candidate = _candidate(db_session)
    row = _translation(candidate)
    row.source = TranslationSource.HUMAN
    db_session.add(row)
    db_session.flush()
    db_session.expire(row)

    assert row.source is TranslationSource.HUMAN


def test_deleting_a_candidate_cascades_to_its_translations_and_tasks(db_session: Session) -> None:
    """translation · deleting a candidate cascades to its index rows and tasks and spares other candidates."""
    doomed, kept = _candidate(db_session), _candidate(db_session)
    for candidate in (doomed, kept):
        db_session.add_all([_translation(candidate), _task(candidate)])
    db_session.flush()

    db_session.execute(delete(DiscoveryDocumentCandidate).where(DiscoveryDocumentCandidate.id == doomed.id))

    assert db_session.execute(select(CandidateTranslation.candidate_id)).scalars().all() == [kept.id]
    assert db_session.execute(select(TranslationTask.candidate_id)).scalars().all() == [kept.id]


def test_one_open_task_per_candidate_and_locale_and_a_completed_one_does_not_block(db_session: Session) -> None:
    """translation task · one open task per candidate and locale; a completed one does not block a new one."""
    candidate = _candidate(db_session)
    db_session.add_all(
        [_task(candidate, WorkTaskStatus.COMPLETED), _task(candidate, WorkTaskStatus.FAILED), _task(candidate)]
    )
    db_session.flush()

    stored = (
        db_session.execute(select(TranslationTask).where(TranslationTask.candidate_id == candidate.id)).scalars().all()
    )

    assert sorted(task.status for task in stored) == sorted(
        [WorkTaskStatus.COMPLETED, WorkTaskStatus.FAILED, WorkTaskStatus.PENDING]
    )
    assert all(task.priority == 100 and task.attempt_count == 0 for task in stored)


@pytest.mark.parametrize("open_status", [WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED])
def test_a_second_open_task_for_the_same_candidate_and_locale_is_refused(
    db_session: Session, open_status: WorkTaskStatus
) -> None:
    """translation task · a second open (pending or claimed) task for the same candidate and locale is refused."""
    candidate = _candidate(db_session)
    db_session.add(_task(candidate, open_status))
    db_session.flush()

    db_session.add(_task(candidate))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_another_locale_of_the_same_candidate_is_a_separate_open_task(db_session: Session) -> None:
    """translation task · the open-task uniqueness is per locale: a second locale is queued beside the first."""
    candidate = _candidate(db_session)
    other = _task(candidate)
    other.locale = "tr"
    db_session.add_all([_task(candidate), other])
    db_session.flush()

    assert len(db_session.execute(select(TranslationTask)).scalars().all()) == 2


def test_deleting_the_claiming_api_key_keeps_the_task_and_clears_the_claimer(db_session: Session) -> None:
    """translation task · deleting the claiming API key keeps the task and clears the claimer."""
    key = ApiKey(name="translate", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(key)
    db_session.flush()
    task = _task(_candidate(db_session), WorkTaskStatus.CLAIMED)
    task.claimed_by_api_key_id = key.id
    db_session.add(task)
    db_session.flush()

    db_session.execute(delete(ApiKey).where(ApiKey.id == key.id))
    db_session.refresh(task)

    assert task.claimed_by_api_key_id is None
    assert task.status is WorkTaskStatus.CLAIMED
