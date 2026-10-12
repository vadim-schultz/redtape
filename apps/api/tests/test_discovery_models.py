"""Tests for discovery staging ORM models (chapter 1)."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models.discovery import (
    CatalogueService,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
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

    db_session.execute(sa.delete(CatalogueService).where(CatalogueService.id == catalogue.id))
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
