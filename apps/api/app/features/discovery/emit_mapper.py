"""Map staging ``discovery_claim`` rows to ``SuggestionCreate`` bodies for preview and emit."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import ValidationError

from app.models.suggestion import SuggestionKind
from app.schema.discovery.claim_payload import (
    MetadataClaimPayload,
    NewDocumentClaimPayload,
    NewRequirementClaimPayload,
)
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload

DiscoveryClaimKind = Literal["new_document", "new_requirement", "metadata"]


class EmitSkipReason(StrEnum):
    """Why a claim does not produce a suggestion body."""

    METADATA_NOT_EMITTED = "metadata_not_emitted"
    UNRESOLVED_REQUIREMENT = "unresolved_requirement"
    INVALID_PAYLOAD = "invalid_payload"


def claim_to_create_body(
    *,
    jurisdiction_id: UUID,
    claim_kind: DiscoveryClaimKind,
    payload: dict,
    entity_canonical_url: str,
) -> tuple[SuggestionCreate | None, EmitSkipReason | None]:
    """Return a create body for emit-ready claims, or ``None`` and a skip reason."""
    if claim_kind == "metadata":
        try:
            MetadataClaimPayload.model_validate(payload)
        except ValidationError:
            return None, EmitSkipReason.INVALID_PAYLOAD
        return None, EmitSkipReason.METADATA_NOT_EMITTED

    if claim_kind == "new_document":
        try:
            doc_claim = NewDocumentClaimPayload.model_validate(payload)
        except ValidationError:
            return None, EmitSkipReason.INVALID_PAYLOAD
        doc_payload = NewDocumentPayload.model_validate(doc_claim.model_dump())
        return _envelope(jurisdiction_id, SuggestionKind.NEW_DOCUMENT, doc_payload, entity_canonical_url), None

    if claim_kind == "new_requirement":
        try:
            req_claim = NewRequirementClaimPayload.model_validate(payload)
        except ValidationError:
            return None, EmitSkipReason.INVALID_PAYLOAD
        if not req_claim.is_emit_ready():
            return None, EmitSkipReason.UNRESOLVED_REQUIREMENT
        req_payload = req_claim.to_suggestion_payload()
        return _envelope(jurisdiction_id, SuggestionKind.NEW_REQUIREMENT, req_payload, entity_canonical_url), None

    raise AssertionError(f"unsupported discovery claim kind: {claim_kind!r}")


def _envelope(
    jurisdiction_id: UUID,
    kind: SuggestionKind,
    payload: NewDocumentPayload | NewRequirementPayload,
    entity_canonical_url: str,
) -> SuggestionCreate:
    return SuggestionCreate(
        kind=kind,
        jurisdiction_id=jurisdiction_id,
        municipality_code=None,
        payload=payload,
        source_url=entity_canonical_url,
    )
