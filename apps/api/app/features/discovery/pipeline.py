"""Pure pipeline stage derivation for discovery staging aggregates."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.discovery import DiscoveryClaimKind


@dataclass(frozen=True, slots=True)
class PipelineStageInput:
    """Counts and flags derived from a catalogue pipeline aggregate."""

    task_count: int
    has_fetch_log: bool
    claim_count: int
    all_emit_claims_resolvable: bool


def derive_pipeline_stage(data: PipelineStageInput) -> str:
    """Return ``T0``–``T4`` using ordered rules from highest to lowest stage."""

    rules: tuple[tuple[bool, str], ...] = (
        (data.claim_count > 0 and data.all_emit_claims_resolvable, "T4"),
        (data.claim_count > 0, "T3"),
        (data.has_fetch_log, "T2"),
        (data.task_count > 0, "T1"),
    )
    for matches, stage in rules:
        if matches:
            return stage
    return "T0"


def claim_emit_resolvable(kind: DiscoveryClaimKind, payload: dict[str, object]) -> bool:
    """Return whether a claim can produce a suggestion payload without stubs."""

    if kind == DiscoveryClaimKind.METADATA:
        return False
    if kind == DiscoveryClaimKind.NEW_DOCUMENT:
        return bool(payload.get("title_i18n")) and bool(payload.get("official_url"))
    if kind == DiscoveryClaimKind.NEW_REQUIREMENT:
        parent = payload.get("parent_document_id")
        required = payload.get("required_document_id")
        return parent is not None and required is not None
    return False


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


