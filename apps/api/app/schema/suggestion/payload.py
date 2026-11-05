"""Pydantic payload schemas for suggestions, validated per `kind`."""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.category_codes import ACTIVE_CATEGORY_CODES
from app.shared.retired_taxonomy import RETIRED_TAXONOMY_FIELDS, retired_taxonomy_message
from app.url_normalization import validate_url

_LOCALE_CODE_RE = re.compile(r"^[a-zA-Z]{2,5}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_TITLE_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 4000
MAX_NOTES_LENGTH = 1000
MAX_CODES = 20


def _validate_locale_key(key: str) -> str:
    if not _LOCALE_CODE_RE.fullmatch(key):
        raise ValueError(f"invalid locale code: {key!r}")
    return key.lower()


def _validate_i18n_value(value: str, *, max_len: int) -> str:
    if _CONTROL_CHAR_RE.search(value):
        raise ValueError("value must not contain control characters")
    trimmed = value.strip()
    if len(trimmed) > max_len:
        raise ValueError(f"value exceeds {max_len} characters")
    return trimmed


def _validate_i18n_map(value: dict[str, str], *, max_len: int) -> dict[str, str]:
    return {_validate_locale_key(key): _validate_i18n_value(val, max_len=max_len) for key, val in value.items()}


def _validate_codes(value: list[str]) -> list[str]:
    if len(value) > MAX_CODES:
        raise ValueError(f"at most {MAX_CODES} codes")
    if len(set(value)) != len(value):
        raise ValueError("codes must be unique")
    return value


class NewDocumentPayload(BaseModel):
    """Payload for a `new_document` suggestion; pure validation, no database lookups."""

    model_config = ConfigDict(extra="forbid")

    title_i18n: dict[str, str]
    description_i18n: dict[str, str] | None = None
    official_url: str | None = None
    category_codes: list[str] = Field(default_factory=list)
    tag_confidence: dict[str, float] | None = None
    pvog_leaf_codes: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_retired_fields(cls, value: object) -> object:
        """Reject retired axis fields with a validation error; a retired field is never silently translated."""
        if isinstance(value, dict):
            retired = sorted(RETIRED_TAXONOMY_FIELDS & value.keys())
            if retired:
                raise ValueError(retired_taxonomy_message(retired))
        return value

    @field_validator("title_i18n")
    @classmethod
    def _check_title_i18n(cls, value: dict[str, str]) -> dict[str, str]:
        validated = _validate_i18n_map(value, max_len=MAX_TITLE_LENGTH)
        if not any(validated.values()):
            raise ValueError("title_i18n must have at least one non-blank value")
        return validated

    @field_validator("description_i18n")
    @classmethod
    def _check_description_i18n(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _validate_i18n_map(value, max_len=MAX_DESCRIPTION_LENGTH)

    @field_validator("official_url")
    @classmethod
    def _check_official_url(cls, value: str | None) -> str | None:
        return None if value is None else validate_url(value)

    @field_validator("category_codes")
    @classmethod
    def _check_codes(cls, value: list[str]) -> list[str]:
        checked = _validate_codes(value)
        unknown = sorted(set(checked) - ACTIVE_CATEGORY_CODES)
        if unknown:
            raise ValueError(f"unknown or inactive category code(s): {', '.join(unknown)}")
        return checked

    @model_validator(mode="after")
    def _check_tag_confidence_keys(self) -> NewDocumentPayload:
        if self.tag_confidence is None:
            return self
        unknown = sorted(set(self.tag_confidence) - set(self.category_codes))
        if unknown:
            raise ValueError(f"tag_confidence keys not in category_codes: {unknown}")
        return self

    @model_validator(mode="after")
    def _check_pvog_leaf_codes_keys(self) -> NewDocumentPayload:
        if self.pvog_leaf_codes is None:
            return self
        unknown = sorted(set(self.pvog_leaf_codes) - set(self.category_codes))
        if unknown:
            raise ValueError(f"pvog_leaf_codes keys not in category_codes: {unknown}")
        return self


class NewRequirementPayload(BaseModel):
    """Payload for a `new_requirement` suggestion; pure validation, no database lookups."""

    model_config = ConfigDict(extra="forbid")

    parent_document_id: UUID
    required_document_id: UUID
    notes_i18n: dict[str, str] | None = None

    @field_validator("notes_i18n")
    @classmethod
    def _check_notes_i18n(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _validate_i18n_map(value, max_len=MAX_NOTES_LENGTH)

    @model_validator(mode="after")
    def _check_ids_differ(self) -> NewRequirementPayload:
        if self.parent_document_id == self.required_document_id:
            raise ValueError("parent_document_id and required_document_id must differ")
        return self
