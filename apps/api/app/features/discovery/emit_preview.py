"""Map staging claims to read-only emit preview rows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict
from uuid import UUID

from app.features.discovery.url_normalize import normalize_canonical_url
from app.models.discovery import DiscoveryClaim, DiscoveryClaimKind, DiscoveryEntity
from app.models.suggestion import SuggestionKind
from app.schema.discovery.emit import SkipReason


class EmitPreviewItem(TypedDict):
    """One row in the admin emit preview response."""

    claim_id: str
    kind: str
    payload: dict[str, object] | None
    skip_reason: SkipReason | None


def _metadata_skip(payload: dict[str, object]) -> SkipReason | None:
    return SkipReason.METADATA_NOT_EMITTED


def _document_skip(payload: dict[str, object]) -> SkipReason | None:
    if not payload.get("title_i18n") or not payload.get("official_url"):
        return SkipReason.INVALID_NEW_DOCUMENT_PAYLOAD
    return None


def _requirement_skip(payload: dict[str, object]) -> SkipReason | None:
    if payload.get("parent_document_id") is None or payload.get("required_document_id") is None:
        return SkipReason.UNRESOLVED_REQUIREMENT_DOCUMENTS
    return None


_SKIP_CHECKS: dict[DiscoveryClaimKind, Callable[[dict[str, object]], SkipReason | None]] = {
    DiscoveryClaimKind.METADATA: _metadata_skip,
    DiscoveryClaimKind.NEW_DOCUMENT: _document_skip,
    DiscoveryClaimKind.NEW_REQUIREMENT: _requirement_skip,
}


def _suggestion_body(claim: DiscoveryClaim, entity: DiscoveryEntity, jurisdiction_id: UUID) -> dict[str, object]:
    return {
        "kind": SuggestionKind(claim.kind.value).value,
        "jurisdiction_id": str(jurisdiction_id),
        "source_url": normalize_canonical_url(entity.canonical_url),
        "payload": claim.payload,
    }


def claim_to_suggestion_payload(
    *,
    claim: DiscoveryClaim,
    entity: DiscoveryEntity,
    jurisdiction_id: UUID,
) -> tuple[dict[str, object] | None, SkipReason | None]:
    """Return suggestion-shaped payload or a skip reason."""
    skip_reason = _SKIP_CHECKS[claim.kind](claim.payload)
    if skip_reason is not None:
        return None, skip_reason
    return _suggestion_body(claim, entity, jurisdiction_id), None


def _preview_item(claim: DiscoveryClaim, payload: dict[str, object] | None, skip: SkipReason | None) -> EmitPreviewItem:
    return {"claim_id": str(claim.id), "kind": claim.kind.value, "payload": payload, "skip_reason": skip}


def _preview_one(claim: DiscoveryClaim, entity: DiscoveryEntity | None, jurisdiction_id: UUID) -> EmitPreviewItem:
    if entity is None:
        return _preview_item(claim, None, SkipReason.MISSING_ENTITY)
    payload, skip_reason = claim_to_suggestion_payload(claim=claim, entity=entity, jurisdiction_id=jurisdiction_id)
    return _preview_item(claim, payload, skip_reason)


def build_emit_preview_items(
    *,
    claims: list[DiscoveryClaim],
    entities_by_id: dict[UUID, DiscoveryEntity],
    jurisdiction_id: UUID,
) -> list[EmitPreviewItem]:
    """Build preview rows for all claims under a catalogue service."""
    return [_preview_one(c, entities_by_id.get(c.discovery_entity_id), jurisdiction_id) for c in claims]
