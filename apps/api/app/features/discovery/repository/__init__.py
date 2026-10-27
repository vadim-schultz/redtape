"""Discovery persistence, split by aggregate."""

from __future__ import annotations

from app.features.discovery.repository.activity import ActivityRepository, FetchLogEntry, NewEvent
from app.features.discovery.repository.artifact_listing import ArtifactFilter, ArtifactListingRepository
from app.features.discovery.repository.artifacts import ArtifactRepository, ArtifactTotals, NewArtifact
from app.features.discovery.repository.budgets import BudgetRepository, LedgerKey, LedgerState
from app.features.discovery.repository.candidate_filter import CandidateFilter, CandidateSort
from app.features.discovery.repository.candidate_listing import CandidateListingRepository
from app.features.discovery.repository.candidates import CandidateRepository
from app.features.discovery.repository.catalogue import CatalogueRepository
from app.features.discovery.repository.claims import ClaimRepository
from app.features.discovery.repository.composite import DiscoveryRepository
from app.features.discovery.repository.coverage import CoverageRepository, DiscoveryCoverageCounts
from app.features.discovery.repository.entities import EntityRepository
from app.features.discovery.repository.queue_metrics import QueueMetricsRepository, TaskStatusCounts, TaskSummary
from app.features.discovery.repository.runs import RunReport, RunRepository
from app.features.discovery.repository.task_listing import Page, TaskFilter, TaskListingRepository
from app.features.discovery.repository.tasks import TaskRepository, TaskTarget

__all__ = [
    "ActivityRepository",
    "ArtifactFilter",
    "ArtifactListingRepository",
    "ArtifactRepository",
    "ArtifactTotals",
    "BudgetRepository",
    "CandidateFilter",
    "CandidateListingRepository",
    "CandidateRepository",
    "CandidateSort",
    "CatalogueRepository",
    "ClaimRepository",
    "CoverageRepository",
    "DiscoveryCoverageCounts",
    "DiscoveryRepository",
    "EntityRepository",
    "FetchLogEntry",
    "LedgerKey",
    "LedgerState",
    "NewArtifact",
    "NewEvent",
    "Page",
    "QueueMetricsRepository",
    "RunReport",
    "RunRepository",
    "TaskFilter",
    "TaskListingRepository",
    "TaskRepository",
    "TaskStatusCounts",
    "TaskSummary",
    "TaskTarget",
]
