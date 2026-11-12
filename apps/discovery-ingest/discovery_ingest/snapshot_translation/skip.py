"""The skip decision: a page is not translated when its cleaned text is too short or it is not German."""

from __future__ import annotations

import enum

from discovery_ingest.snapshot_translation.limits import MIN_TEXT_CHARS


class SkipReason(enum.StrEnum):
    """Why a page is skipped; the values are the ``skipped_reason`` the API accepts."""

    TOO_SHORT = "too_short"
    NOT_GERMAN = "not_german"


def skip_reason(text: str, language: str | None) -> SkipReason | None:
    """Return why a page with cleaned ``text`` and primary ``language`` is skipped, or ``None`` when it is translated.

    Length is checked first, so an empty page is ``too_short`` whatever its language. A page that declares no
    language is not German as far as the page says, so it is ``not_german``.
    """
    if len(text) < MIN_TEXT_CHARS:
        return SkipReason.TOO_SHORT
    if language != "de":
        return SkipReason.NOT_GERMAN
    return None
