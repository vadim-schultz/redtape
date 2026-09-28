"""Request schema for creating a suggestion, validated per `kind`."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.suggestion import SuggestionKind
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload, validate_url

_PAYLOAD_TYPES: dict[SuggestionKind, type[BaseModel]] = {
    SuggestionKind.NEW_DOCUMENT: NewDocumentPayload,
    SuggestionKind.NEW_REQUIREMENT: NewRequirementPayload,
}


class SuggestionCreate(BaseModel):
    """`POST /api/v1/suggestions` body; `payload`'s shape is discriminated on `kind`."""

    model_config = ConfigDict(extra="forbid")

    kind: SuggestionKind = SuggestionKind.NEW_DOCUMENT
    payload: NewDocumentPayload | NewRequirementPayload
    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    source_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_payload_for_kind(cls, data: object) -> object:
        if not isinstance(data, dict) or not isinstance(data.get("payload"), dict):
            return data
        payload_type = _PAYLOAD_TYPES[SuggestionKind(data.get("kind", SuggestionKind.NEW_DOCUMENT))]
        return {**data, "payload": payload_type.model_validate(data["payload"])}

    @field_validator("source_url")
    @classmethod
    def _check_source_url(cls, value: str | None) -> str | None:
        return None if value is None else validate_url(value, field="source_url")

    @model_validator(mode="after")
    def _check_jurisdiction_xor(self) -> SuggestionCreate:
        if (self.jurisdiction_id is None) == (self.municipality_code is None):
            raise ValueError("exactly one of jurisdiction_id or municipality_code is required")
        return self
