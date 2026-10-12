"""Pydantic payloads for ``discovery_claim.payload``, aligned with suggestion kinds."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schema.suggestion.payload import (
    MAX_NOTES_LENGTH,
    NewDocumentPayload,
    NewRequirementPayload,
    _validate_i18n_map,
)


class NewDocumentClaimPayload(NewDocumentPayload):
    """Staging claim for a proposed document; identical validation to ``NewDocumentPayload``."""


class NewRequirementClaimPayload(BaseModel):
    """Staging claim for a dependency edge; emit skips until both document UUIDs are set (D8)."""

    model_config = ConfigDict(extra="forbid")

    parent_document_id: UUID | None = None
    required_document_id: UUID | None = None
    notes_i18n: dict[str, str] | None = None

    @model_validator(mode="after")
    def _check_ids_differ_when_both_set(self) -> NewRequirementClaimPayload:
        if (
            self.parent_document_id is not None
            and self.required_document_id is not None
            and self.parent_document_id == self.required_document_id
        ):
            raise ValueError("parent_document_id and required_document_id must differ")
        return self

    def is_emit_ready(self) -> bool:
        return self.parent_document_id is not None and self.required_document_id is not None

    def to_suggestion_payload(self) -> NewRequirementPayload:
        parent_id = self.parent_document_id
        required_id = self.required_document_id
        if parent_id is None or required_id is None:
            raise ValueError("requirement claim is not emit-ready")
        return NewRequirementPayload(
            parent_document_id=parent_id,
            required_document_id=required_id,
            notes_i18n=self.notes_i18n,
        )


class MetadataClaimPayload(BaseModel):
    """Non-emitted enrich notes; admin preview only."""

    model_config = ConfigDict(extra="forbid")

    notes_i18n: dict[str, str] | None = None

    @field_validator("notes_i18n")
    @classmethod
    def _check_notes_i18n(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _validate_i18n_map(value, max_len=MAX_NOTES_LENGTH)
