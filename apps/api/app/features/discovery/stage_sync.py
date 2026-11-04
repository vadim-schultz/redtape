"""Persist catalogue pipeline stage advances on the machine write path."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.pipeline import PipelineStage, derive_pipeline_stage, stage_input
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import CatalogueService


def derive_stage_for(repo: DiscoveryRepository, catalogue_id: UUID) -> PipelineStage:
    """Return the stage implied by the stored tasks, fetch logs and claims."""
    return derive_pipeline_stage(
        stage_input(
            task_count=int(repo.catalogue_has_tasks(catalogue_id)),
            has_fetch_log=repo.catalogue_has_fetch_log(catalogue_id),
            claims=repo.catalogue_claim_kinds_and_payloads(catalogue_id),
        )
    )


def advance_stage(repo: DiscoveryRepository, catalogue: CatalogueService) -> None:
    """Keep the stored stage in step with the evidence; stages only move forward."""
    stored = PipelineStage(catalogue.pipeline_stage)
    if stored is PipelineStage.T4:
        return
    derived = derive_stage_for(repo, catalogue.id)
    if derived.rank > stored.rank:
        catalogue.pipeline_stage = derived.value
