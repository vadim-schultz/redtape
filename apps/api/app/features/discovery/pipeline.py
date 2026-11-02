"""Pure pipeline stage derivation for discovery staging aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.discovery import DiscoveryClaimKind


class PipelineStage(StrEnum):
    """Ordered catalogue pipeline stages persisted in ``pipeline_stage``."""

    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"

    @property
    def rank(self) -> int:
        """Return the numeric position of the stage (``T0`` is 0)."""
        return int(self.value[1:])


@dataclass(frozen=True, slots=True)
class PipelineStageInput:
    """Counts and flags derived from a catalogue pipeline aggregate."""

    task_count: int
    has_fetch_log: bool
    claim_count: int
    all_emit_claims_resolvable: bool


def derive_pipeline_stage(data: PipelineStageInput) -> PipelineStage:
    """Return ``T0``–``T4`` using ordered rules from highest to lowest stage."""
    rules: tuple[tuple[bool, PipelineStage], ...] = (
        (data.claim_count > 0 and data.all_emit_claims_resolvable, PipelineStage.T4),
        (data.claim_count > 0, PipelineStage.T3),
        (data.has_fetch_log, PipelineStage.T2),
        (data.task_count > 0, PipelineStage.T1),
    )
    for matches, stage in rules:
        if matches:
            return stage
    return PipelineStage.T0


def claim_emit_resolvable(kind: DiscoveryClaimKind, payload: dict[str, object]) -> bool:
    """Return whether a claim can produce a suggestion payload without stubs."""
    match kind:
        case DiscoveryClaimKind.METADATA:
            return False
        case DiscoveryClaimKind.NEW_DOCUMENT:
            return bool(payload.get("title_i18n")) and bool(payload.get("official_url"))
        case DiscoveryClaimKind.NEW_REQUIREMENT:
            parent = payload.get("parent_document_id")
            required = payload.get("required_document_id")
            return parent is not None and required is not None


def all_emit_claims_resolvable(
    claims: list[tuple[DiscoveryClaimKind, dict[str, object]]],
) -> bool:
    """Return whether every emit-eligible claim is resolvable."""
    emit_claims = [
        (kind, payload)
        for kind, payload in claims
        if kind in (DiscoveryClaimKind.NEW_DOCUMENT, DiscoveryClaimKind.NEW_REQUIREMENT)
    ]
    if not emit_claims:
        return False
    return all(claim_emit_resolvable(kind, payload) for kind, payload in emit_claims)
