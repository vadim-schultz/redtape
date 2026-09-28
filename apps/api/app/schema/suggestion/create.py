"""Request schema for creating a suggestion, validated per `kind`."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.suggestion import SuggestionKind
from app.schema.suggestion.payload import NewDocumentPayload, validate_url


class SuggestionCreate(BaseModel):
    """`POST /api/v1/suggestions` body. `payload` gains more kinds as they ship."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[SuggestionKind.NEW_DOCUMENT] = SuggestionKind.NEW_DOCUMENT
    payload: NewDocumentPayload
    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    source_url: str | None = None

    @field_validator("source_url")
    @classmethod
    def _check_source_url(cls, value: str | None) -> str | None:
        return None if value is None else validate_url(value, field="source_url")

    @model_validator(mode="after")
    def _check_jurisdiction_xor(self) -> SuggestionCreate:
        if (self.jurisdiction_id is None) == (self.municipality_code is None):
            raise ValueError("exactly one of jurisdiction_id or municipality_code is required")
        return self
