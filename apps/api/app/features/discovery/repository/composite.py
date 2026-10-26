"""Composite of the per-aggregate discovery repositories."""

from __future__ import annotations

from app.features.discovery.repository.activity import ActivityRepository
from app.features.discovery.repository.artifact_listing import ArtifactListingRepository
from app.features.discovery.repository.artifacts import ArtifactRepository
from app.features.discovery.repository.candidate_listing import CandidateListingRepository
from app.features.discovery.repository.candidates import CandidateRepository
from app.features.discovery.repository.catalogue import CatalogueRepository
from app.features.discovery.repository.claims import ClaimRepository
from app.features.discovery.repository.coverage import CoverageRepository
from app.features.discovery.repository.entities import EntityRepository
from app.features.discovery.repository.runs import RunRepository
from app.features.discovery.repository.task_listing import TaskListingRepository
from app.features.discovery.repository.tasks import TaskRepository


class DiscoveryRepository(
    CatalogueRepository,
    TaskRepository,
    TaskListingRepository,
    EntityRepository,
    ClaimRepository,
    CandidateRepository,
    CandidateListingRepository,
    ActivityRepository,
    ArtifactListingRepository,
    CoverageRepository,
    RunRepository,
    ArtifactRepository,
):
    """One session-bound handle exposing every discovery aggregate repository."""
