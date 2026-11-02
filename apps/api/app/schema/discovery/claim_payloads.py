"""Validated JSON shapes for ``discovery_claim.payload`` by kind."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.discovery import DiscoveryClaimKind


class MetadataClaimPayload(BaseModel):
    """Non-emit staging metadata extracted during enrich."""

    kurztext: str | None = Field(default=None, max_length=5000)
    description_i18n: dict[str, str] | None = None


class NewDocumentClaimPayload(BaseModel):
    """Stub for a document suggestion before emit."""

    title_i18n: dict[str, str] = Field(min_length=1)
    official_url: str = Field(min_length=1, max_length=500)


class NewRequirementClaimPayload(BaseModel):
    """Requirement edge; may reference unresolved document ids (D8)."""

    parent_document_id: UUID | None = None
    required_document_id: UUID | None = None


def validate_claim_payload(kind: DiscoveryClaimKind, payload: dict[str, object]) -> dict[str, object]:
    """Validate and normalize a claim payload for ``kind``."""
    match kind:
        case DiscoveryClaimKind.METADATA:
            return MetadataClaimPayload.model_validate(payload).model_dump(exclude_none=True)
        case DiscoveryClaimKind.NEW_DOCUMENT:
            return NewDocumentClaimPayload.model_validate(payload).model_dump(exclude_none=True)
        case DiscoveryClaimKind.NEW_REQUIREMENT:
            return NewRequirementClaimPayload.model_validate(payload).model_dump(exclude_none=True)
