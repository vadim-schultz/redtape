"""Load-or-raise helpers shared by discovery services."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.errors import (
    CatalogueNotFoundError,
    DiscoveryRunNotFoundError,
    DiscoveryTaskNotFoundError,
)
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import CatalogueService, DiscoveryRun, DiscoveryTask


def require_catalogue(repo: DiscoveryRepository, catalogue_id: UUID) -> CatalogueService:
    """Return the catalogue row or raise ``CatalogueNotFoundError``."""
    row = repo.get_catalogue(catalogue_id)
    if row is None:
        raise CatalogueNotFoundError()
    return row


def require_task(repo: DiscoveryRepository, task_id: UUID) -> DiscoveryTask:
    """Return the task row or raise ``DiscoveryTaskNotFoundError``."""
    task = repo.get_task(task_id)
    if task is None:
        raise DiscoveryTaskNotFoundError()
    return task


def require_run(repo: DiscoveryRepository, run_id: UUID) -> DiscoveryRun:
    """Return the run row or raise ``DiscoveryRunNotFoundError``."""
    run = repo.get_run(run_id)
    if run is None:
        raise DiscoveryRunNotFoundError()
    return run
