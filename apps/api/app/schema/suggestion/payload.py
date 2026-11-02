"""Pydantic payload schemas for suggestions, validated per `kind`."""

from __future__ import annotations

import re
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_LOCALE_CODE_RE = re.compile(r"^[a-zA-Z]{2,5}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_TITLE_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 4000
MAX_URL_LENGTH = 500
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


def validate_url(value: str, *, field: str = "official_url") -> str:
    if len(value) > MAX_URL_LENGTH:
        raise ValueError(f"{field} exceeds {MAX_URL_LENGTH} characters")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{field} must use http or https")
    if not parsed.netloc:
        raise ValueError(f"{field} must include a host")
    return value


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
    domain_codes: list[str] = Field(default_factory=list)
    situation_codes: list[str] = Field(default_factory=list)
    tag_confidence: dict[str, float] | None = None

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

    @field_validator("domain_codes", "situation_codes")
    @classmethod
    def _check_codes(cls, value: list[str]) -> list[str]:
        return _validate_codes(value)

    @model_validator(mode="after")
    def _check_tag_confidence_keys(self) -> NewDocumentPayload:
        if self.tag_confidence is None:
            return self
        known = set(self.domain_codes) | set(self.situation_codes)
        unknown = sorted(set(self.tag_confidence) - known)
        if unknown:
            raise ValueError(f"tag_confidence keys not in domain_codes/situation_codes: {unknown}")
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
