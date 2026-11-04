"""The discovery machine service takes its collaborators instead of building them (B3, L11)."""

from __future__ import annotations

import inspect

from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_ingest import ClaimIngest
from app.features.discovery.dependencies import provide_discovery_machine_service
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryMachineService
from app.features.discovery.task_queue import TaskQueue
from sqlalchemy.orm import Session


def test_discovery_machine_service_receives_its_collaborators(db_session: Session) -> None:
    repo = DiscoveryRepository(db_session)
    upserts = CatalogueUpsertService(repo)
    queue = TaskQueue(repo)
    claim_ingest = ClaimIngest(repo)

    service = DiscoveryMachineService(repo, upserts, queue, claim_ingest)

    assert service._catalogue_upserts is upserts
    assert service._queue is queue
    assert service._claim_ingest is claim_ingest


def test_discovery_machine_service_signature_lists_every_collaborator() -> None:
    parameters = list(inspect.signature(DiscoveryMachineService.__init__).parameters)

    assert parameters == ["self", "repository", "catalogue_upserts", "queue", "claim_ingest"]


def test_provider_wires_the_collaborators_for_one_repository(db_session: Session) -> None:
    repo = DiscoveryRepository(db_session)

    service = provide_discovery_machine_service(repo)

    assert isinstance(service._catalogue_upserts, CatalogueUpsertService)
    assert isinstance(service._queue, TaskQueue)
    assert isinstance(service._claim_ingest, ClaimIngest)
