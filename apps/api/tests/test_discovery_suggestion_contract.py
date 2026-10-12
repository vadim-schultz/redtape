"""Contract tests: discovery emit mapper output must validate as suggestion create bodies."""

from __future__ import annotations

import uuid

from app.features.discovery.emit_mapper import EmitSkipReason, claim_to_create_body
from app.models.suggestion import SuggestionKind
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload


def test_claim_to_create_body_maps_new_document() -> None:
    jurisdiction_id = uuid.uuid4()
    body, skip = claim_to_create_body(
        jurisdiction_id=jurisdiction_id,
        claim_kind="new_document",
        payload={
            "title_i18n": {"de": "Meldebescheinigung"},
            "official_url": "https://example.gov/form",
            "domain_codes": ["housing"],
            "situation_codes": [],
        },
        entity_canonical_url="https://example.gov/form",
    )
    assert skip is None
    assert body is not None
    assert body.kind == SuggestionKind.NEW_DOCUMENT
    assert body.jurisdiction_id == jurisdiction_id
    assert body.source_url == "https://example.gov/form"
    assert isinstance(body.payload, NewDocumentPayload)
    NewDocumentPayload.model_validate(body.payload.model_dump())


def test_claim_to_create_body_skips_unresolved_requirement() -> None:
    body, skip = claim_to_create_body(
        jurisdiction_id=uuid.uuid4(),
        claim_kind="new_requirement",
        payload={"parent_document_id": None, "required_document_id": None},
        entity_canonical_url="https://example.gov/page",
    )
    assert body is None
    assert skip == EmitSkipReason.UNRESOLVED_REQUIREMENT


def test_claim_to_create_body_maps_resolved_requirement() -> None:
    parent = uuid.uuid4()
    required = uuid.uuid4()
    body, skip = claim_to_create_body(
        jurisdiction_id=uuid.uuid4(),
        claim_kind="new_requirement",
        payload={"parent_document_id": str(parent), "required_document_id": str(required)},
        entity_canonical_url="https://example.gov/page",
    )
    assert skip is None
    assert body is not None
    assert isinstance(body.payload, NewRequirementPayload)
    NewRequirementPayload.model_validate(body.payload.model_dump())


def test_claim_to_create_body_skips_metadata() -> None:
    body, skip = claim_to_create_body(
        jurisdiction_id=uuid.uuid4(),
        claim_kind="metadata",
        payload={"notes_i18n": {"de": "Hinweis"}},
        entity_canonical_url="https://example.gov/page",
    )
    assert body is None
    assert skip == EmitSkipReason.METADATA_NOT_EMITTED
