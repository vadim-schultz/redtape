"""Lenient readers for external JSON: the text rules the crawl ladders share, and the Pydantic validators for them."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


def optional_str(value: object) -> str | None:
    """Return ``value`` stripped, coercing any non-string with ``str()``, or ``None`` when it is blank."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value).strip() or None


def text_or_none(value: object) -> str | None:
    """Return ``value`` stripped when it is a non-blank string; any other value gives ``None``."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def first_present(*values: str | None) -> str | None:
    """Return the first non-blank value in order, or ``None`` when every value is blank."""
    for value in values:
        if value:
            return value
    return None


def list_or_empty(value: object) -> list[object]:
    """Return the entries of a JSON array, or no entries when the value is not an array."""
    return list(value) if isinstance(value, list) else []


def dicts_only(value: object) -> list[dict[str, object]]:
    """Return the object entries of a JSON array, dropping every other entry; no entries for a non-array."""
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def dicts_or_none(value: object) -> list[dict[str, object]] | None:
    """Return the object entries of a JSON array, or ``None`` when the value is not an array."""
    if not isinstance(value, list):
        return None
    return [entry for entry in value if isinstance(entry, dict)]


def dict_or_empty(value: object) -> dict[str, object]:
    """Return the value when it is a JSON object, otherwise an empty object."""
    return value if isinstance(value, dict) else {}


def dict_or_none(value: object) -> dict[str, object] | None:
    """Return the value when it is a JSON object, otherwise ``None``."""
    return value if isinstance(value, dict) else None


LenientText = Annotated[str | None, BeforeValidator(optional_str)]
"""Text read the way the crawl always read it: a non-string is coerced with ``str()`` and blank becomes ``None``."""

StrText = Annotated[str | None, BeforeValidator(text_or_none)]
"""Text read as strings only: a non-string is ignored and blank becomes ``None``."""


class WireModel(BaseModel):
    """Base for external payload models: unknown keys are ignored and the parsed values never change."""

    model_config = ConfigDict(extra="ignore", frozen=True)
