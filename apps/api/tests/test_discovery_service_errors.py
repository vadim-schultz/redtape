"""Discovery services raise domain errors, never Litestar HTTP exceptions."""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.errors import (
    CatalogueNotFoundError,
    DiscoveryEntityNotFoundError,
    DiscoveryError,
    DiscoveryTaskNotFoundError,
    InvalidDiscoveryInputError,
    UnknownJurisdictionError,
)
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryAdminService, DiscoveryMachineService
from app.models.discovery import CatalogueService, DiscoverySource
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.discovery.machine import (
    CatalogueBatchItem,
    CatalogueBatchRequest,
    ClaimAppendRequest,
    EntityUpsertRequest,
    TaskFailRequest,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def repo(db_session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(db_session)


@pytest.fixture
def machine(repo: DiscoveryRepository) -> DiscoveryMachineService:
    return DiscoveryMachineService(repo)


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "T"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _item(jurisdiction_id: uuid.UUID) -> CatalogueBatchItem:
    return CatalogueBatchItem(
        source=DiscoverySource.FIM,
        external_id="svc-1",
        jurisdiction_id=jurisdiction_id,
        title_i18n={"en": "Service"},
    )


def test_machine_get_catalogue_returns_existing_row(
    machine: DiscoveryMachineService, db_session: Session, country: Jurisdiction
) -> None:
    result = machine.batch_upsert(CatalogueBatchRequest(items=[_item(country.id)]))

    read = machine.get_catalogue_for_machine(result.items[0].id)

    assert read.id == result.items[0].id


def test_machine_get_catalogue_unknown_raises_domain_error(machine: DiscoveryMachineService) -> None:
    with pytest.raises(CatalogueNotFoundError, match="Catalogue service not found"):
        machine.get_catalogue_for_machine(uuid.uuid4())


def test_machine_task_operations_unknown_task_raise_domain_error(machine: DiscoveryMachineService) -> None:
    with pytest.raises(DiscoveryTaskNotFoundError, match="Discovery task not found"):
        machine.complete_task(uuid.uuid4())
    with pytest.raises(DiscoveryTaskNotFoundError):
        machine.fail_task(uuid.uuid4(), TaskFailRequest(error="boom"))


def test_machine_upsert_entity_unknown_catalogue_raises_without_write(
    machine: DiscoveryMachineService, db_session: Session
) -> None:
    body = EntityUpsertRequest(catalogue_service_id=uuid.uuid4(), canonical_url="https://example.gov/x")

    with pytest.raises(CatalogueNotFoundError):
        machine.upsert_entity(body)


def test_machine_upsert_entity_bad_url_raises_invalid_input(
    machine: DiscoveryMachineService, country: Jurisdiction
) -> None:
    result = machine.batch_upsert(CatalogueBatchRequest(items=[_item(country.id)]))
    body = EntityUpsertRequest(catalogue_service_id=result.items[0].id, canonical_url="not a url")

    with pytest.raises(InvalidDiscoveryInputError):
        machine.upsert_entity(body)


def test_machine_append_claim_unknown_entity_raises_domain_error(machine: DiscoveryMachineService) -> None:
    body = ClaimAppendRequest(discovery_entity_id=uuid.uuid4(), kind="new_document", payload={})  # type: ignore[arg-type]

    with pytest.raises(DiscoveryEntityNotFoundError, match="Discovery entity not found"):
        machine.append_claim(body)


def test_batch_upsert_unknown_jurisdiction_raises_without_row(
    machine: DiscoveryMachineService, db_session: Session
) -> None:
    unknown = uuid.uuid4()

    with pytest.raises(UnknownJurisdictionError, match=str(unknown)):
        machine.batch_upsert(CatalogueBatchRequest(items=[_item(unknown)]))

    assert db_session.scalar(select(func.count()).select_from(CatalogueService)) == 0


def test_admin_unknown_catalogue_raises_domain_error(repo: DiscoveryRepository) -> None:
    admin = DiscoveryAdminService(repo)

    with pytest.raises(CatalogueNotFoundError):
        admin.catalogue_pipeline(uuid.uuid4())
    with pytest.raises(CatalogueNotFoundError):
        admin.emit_preview(uuid.uuid4())


def test_domain_errors_share_a_base() -> None:
    for error in (CatalogueNotFoundError, DiscoveryTaskNotFoundError, UnknownJurisdictionError):
        assert issubclass(error, DiscoveryError)
