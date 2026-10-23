"""Tests for discovery staging ORM models (chapter 1)."""

from __future__ import annotations

import uuid

import pytest
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryMentionRole,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _jurisdiction(session: Session) -> Jurisdiction:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    session.add(country)
    session.flush()
    return country


def _catalogue_service(session: Session, *, external_id: str = "svc-1") -> CatalogueService:
    jurisdiction = _jurisdiction(session)
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=external_id,
        jurisdiction_id=jurisdiction.id,
        title_i18n={"de": "Leistung"},
        raw_payload={"id": external_id},
        pipeline_stage="T0",
    )
    session.add(row)
    session.flush()
    return row


def test_catalogue_service_unique_source_external_id_rejects_duplicate(db_session: Session) -> None:
    first = _catalogue_service(db_session, external_id="dup-ext")
    duplicate = CatalogueService(
        source=first.source,
        external_id=first.external_id,
        jurisdiction_id=first.jurisdiction_id,
        title_i18n={"de": "Other"},
        raw_payload={},
        pipeline_stage="T0",
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_discovery_task_defaults_to_pending_status(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
    )
    db_session.add(task)
    db_session.flush()
    db_session.expire(task)

    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.priority == 100


def test_discovery_entity_cascade_delete_when_catalogue_service_removed(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue.id,
        canonical_url="https://example.gov/form.pdf",
    )
    db_session.add(entity)
    db_session.flush()
    entity_id = entity.id

    db_session.delete(catalogue)
    db_session.flush()

    assert db_session.get(DiscoveryEntity, entity_id) is None


def test_discovery_event_records_event_type_and_optional_fks(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
    )
    db_session.add(task)
    db_session.flush()

    event = DiscoveryEvent(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=catalogue.id,
        discovery_task_id=task.id,
        payload={"kind": "fetch_url"},
    )
    db_session.add(event)
    db_session.flush()
    db_session.expire(event)

    loaded = db_session.get(DiscoveryEvent, event.id)
    assert loaded is not None
    assert loaded.event_type == DiscoveryEventType.TASK_ENQUEUED
    assert loaded.catalogue_service_id == catalogue.id
    assert loaded.discovery_task_id == task.id
    assert loaded.payload == {"kind": "fetch_url"}


def test_pipeline_stage_check_rejects_t9(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    row = CatalogueService(
        source=DiscoverySource.MANUAL,
        external_id="bad-stage",
        jurisdiction_id=jurisdiction.id,
        title_i18n={"en": "x"},
        raw_payload={},
        pipeline_stage="T9",
    )
    db_session.add(row)

    with pytest.raises(IntegrityError):
        db_session.flush()


def _candidate(
    session: Session, jurisdiction_id: uuid.UUID, *, key: str = "personalausweis"
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(jurisdiction_id=jurisdiction_id, key=key, title_i18n={"de": "Personalausweis"})
    session.add(row)
    session.flush()
    return row


def _mention(
    candidate: DiscoveryDocumentCandidate,
    catalogue: CatalogueService,
    *,
    role: DiscoveryMentionRole = DiscoveryMentionRole.REQUIRED,
    source_field: str = "details[0]",
) -> DiscoveryCandidateMention:
    return DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=catalogue.id,
        role=role,
        excerpt="Bitte Personalausweis mitbringen",
        source_field=source_field,
        extractor="pvog_payload",
        extractor_version="1",
    )


def test_candidate_defaults_to_staged_without_suggestion(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.expire(candidate)

    assert candidate.status == DiscoveryCandidateStatus.STAGED
    assert candidate.suggestion_id is None
    assert candidate.official_url is None


def test_candidate_unique_per_jurisdiction_and_key(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(
        DiscoveryDocumentCandidate(
            jurisdiction_id=catalogue.jurisdiction_id, key="personalausweis", title_i18n={"en": "ID card"}
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_candidate_key_may_repeat_across_jurisdictions(db_session: Session) -> None:
    first = _catalogue_service(db_session, external_id="svc-a")
    second = _catalogue_service(db_session, external_id="svc-b")

    _candidate(db_session, first.jurisdiction_id)
    _candidate(db_session, second.jurisdiction_id)


def test_mention_unique_per_candidate_service_role_and_field(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(_mention(candidate, catalogue))
    db_session.flush()
    db_session.add(_mention(candidate, catalogue))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_mention_may_repeat_with_another_role(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(_mention(candidate, catalogue))
    db_session.add(_mention(candidate, catalogue, role=DiscoveryMentionRole.FORM))

    db_session.flush()


def test_deleting_a_catalogue_row_cascades_its_mentions(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    mention = _mention(candidate, catalogue)
    db_session.add(mention)
    db_session.flush()
    mention_id = mention.id

    db_session.delete(catalogue)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryCandidateMention, mention_id) is None
    assert db_session.get(DiscoveryDocumentCandidate, candidate.id) is not None


def test_deleting_a_candidate_cascades_its_mentions(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    mention = _mention(candidate, catalogue)
    db_session.add(mention)
    db_session.flush()
    mention_id = mention.id

    db_session.delete(candidate)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryCandidateMention, mention_id) is None
