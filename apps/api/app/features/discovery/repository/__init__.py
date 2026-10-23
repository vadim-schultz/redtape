"""Discovery persistence, split by aggregate."""

from __future__ import annotations

from app.features.discovery.repository.activity import ActivityRepository, FetchLogEntry, NewEvent
from app.features.discovery.repository.catalogue import CatalogueRepository
from app.features.discovery.repository.claims import ClaimRepository
from app.features.discovery.repository.composite import DiscoveryRepository
from app.features.discovery.repository.coverage import CoverageRepository, DiscoveryCoverageCounts
from app.features.discovery.repository.entities import EntityRepository
from app.features.discovery.repository.queue_metrics import QueueMetricsRepository, TaskStatusCounts
from app.features.discovery.repository.runs import RunReport, RunRepository
from app.features.discovery.repository.task_listing import Page, TaskListingRepository
from app.features.discovery.repository.tasks import TaskRepository, TaskTarget

__all__ = [
    "ActivityRepository",
    "CatalogueRepository",
    "ClaimRepository",
    "CoverageRepository",
    "DiscoveryCoverageCounts",
    "DiscoveryRepository",
    "EntityRepository",
    "FetchLogEntry",
    "NewEvent",
    "Page",
    "QueueMetricsRepository",
    "RunReport",
    "RunRepository",
    "TaskListingRepository",
    "TaskRepository",
    "TaskStatusCounts",
    "TaskTarget",
]
