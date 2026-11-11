"""One validator for JSONB locale keys, shared by every schema that accepts an i18n map."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator

from app.shared.locale import SUPPORTED_LOCALE_CODES


def validate_locale_key(key: str) -> str:
    """Return ``key`` lowercased when it is a supported locale code; raise naming the key otherwise."""
    code = key.lower()
    if code not in SUPPORTED_LOCALE_CODES:
        raise ValueError(f"unsupported locale code: {key!r}")
    return code


def validate_locale_keys(value: dict[str, str]) -> dict[str, str]:
    """Return ``value`` with every key validated and lowercased; values are untouched."""
    return {validate_locale_key(key): text for key, text in value.items()}


LocaleKeyedMap = Annotated[dict[str, str], AfterValidator(validate_locale_keys)]
"""A ``dict[str, str]`` whose keys must be supported locale codes."""
