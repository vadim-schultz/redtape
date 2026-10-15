"""Map staging claims to read-only emit preview rows."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from app.models.discovery import DiscoveryClaim, DiscoveryClaimKind, DiscoveryEntity
from app.models.suggestion import SuggestionKind


class EmitPreviewItem(TypedDict):
    """One row in the admin emit preview response."""

    claim_id: str
    kind: str
    payload: dict[str, object] | None
    skip_reason: str | None


def _claim_to_suggestion_payload(
    *,
    claim: DiscoveryClaim,
    entity: DiscoveryEntity,
    jurisdiction_id: UUID,
) -> tuple[dict[str, object] | None, str | None]:
    """Return suggestion-shaped payload or a skip reason."""

    match claim.kind:
        case DiscoveryClaimKind.METADATA:
            return None, "metadata_not_emitted"
        case DiscoveryClaimKind.NEW_DOCUMENT:
            title_i18n = claim.payload.get("title_i18n")
            official_url = claim.payload.get("official_url")
            if not title_i18n or not official_url:
                return None, "invalid_new_document_payload"
            body: dict[str, object] = {
                "kind": SuggestionKind.NEW_DOCUMENT.value,
                "jurisdiction_id": str(jurisdiction_id),
                "source_url": entity.canonical_url,
                "payload": claim.payload,
            }
            return body, None
        case DiscoveryClaimKind.NEW_REQUIREMENT:
            parent = claim.payload.get("parent_document_id")
            required = claim.payload.get("required_document_id")
            if parent is None or required is None:
                return None, "unresolved_requirement_documents"
            body = {
                "kind": SuggestionKind.NEW_REQUIREMENT.value,
                "jurisdiction_id": str(jurisdiction_id),
                "source_url": entity.canonical_url,
                "payload": claim.payload,
            }
            return body, None


def build_emit_preview_items(
    *,
    claims: list[DiscoveryClaim],
    entities_by_id: dict[UUID, DiscoveryEntity],
    jurisdiction_id: UUID,
) -> list[EmitPreviewItem]:
    """Build preview rows for all claims under a catalogue service."""

    items: list[EmitPreviewItem] = []
    for claim in claims:
        entity = entities_by_id.get(claim.discovery_entity_id)
        if entity is None:
            items.append(
                {
                    "claim_id": str(claim.id),
                    "kind": claim.kind.value,
                    "payload": None,
                    "skip_reason": "missing_entity",
                }
            )
            continue
        payload, skip_reason = _claim_to_suggestion_payload(
            claim=claim,
            entity=entity,
            jurisdiction_id=jurisdiction_id,
        )
        items.append(
            {
                "claim_id": str(claim.id),
                "kind": claim.kind.value,
                "payload": payload,
                "skip_reason": skip_reason,
            }
        )
    return items
