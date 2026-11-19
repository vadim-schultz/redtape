"""Test composition of the discovery machine service from its collaborators."""

from __future__ import annotations

from datetime import timedelta

from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_ingest import ClaimIngest
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryMachineService
from app.features.discovery.task_queue import TaskQueue


def machine_service(repository: DiscoveryRepository) -> DiscoveryMachineService:
    """Build the machine service the way the app's dependency provider does."""
    return DiscoveryMachineService(
        repository,
        CatalogueUpsertService(repository),
        TaskQueue(repository),
        ClaimIngest(repository),
        refresh_max_age=timedelta(days=30),
    )
