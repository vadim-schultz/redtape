"""Persist catalogue pipeline stage advances on the machine write path."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.pipeline import (
    PipelineStage,
    PipelineStageInput,
    all_emit_claims_resolvable,
    derive_pipeline_stage,
)
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import CatalogueService


def derive_stage_for(repo: DiscoveryRepository, catalogue_id: UUID) -> PipelineStage:
    """Return the stage implied by the stored tasks, fetch logs and claims."""

    claims = repo.list_catalogue_claims(catalogue_id)
    return derive_pipeline_stage(
        PipelineStageInput(
            task_count=len(repo.list_catalogue_tasks(catalogue_id)),
            has_fetch_log=len(repo.list_catalogue_fetch_logs(catalogue_id)) > 0,
            claim_count=len(claims),
            all_emit_claims_resolvable=all_emit_claims_resolvable([(c.kind, c.payload) for c in claims]),
        )
    )


def advance_stage(repo: DiscoveryRepository, catalogue: CatalogueService) -> None:
    """Raise ``catalogue.pipeline_stage`` to the derived stage; never move it back."""

    derived = derive_stage_for(repo, catalogue.id)
    if derived.rank > PipelineStage(catalogue.pipeline_stage).rank:
        catalogue.pipeline_stage = derived.value
