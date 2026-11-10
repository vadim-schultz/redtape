"""Bounds of translated text, enforced by the validators the suggestion payloads use."""

from __future__ import annotations

from dataclasses import dataclass

from app.schema.suggestion.payload import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH, validate_i18n_value
from app.schema.translation.machine import TranslationCompleteItem


class InvalidTextError(ValueError):
    """A translated text is empty, too long or holds a control character; the message names the field."""


@dataclass(frozen=True, slots=True)
class CleanText:
    """A translated title and description, trimmed and within bounds."""

    title: str
    description: str


def _field(name: str, value: str, max_len: int) -> str:
    try:
        return validate_i18n_value(value, max_len=max_len)
    except ValueError as err:
        raise InvalidTextError(f"{name}: {err}") from err


def clean(item: TranslationCompleteItem) -> CleanText:
    """Return the trimmed text of ``item``; raise :exc:`InvalidTextError` when it is out of bounds.

    The title must not be empty and holds at most 300 characters; the description holds at most 4000.
    """
    title = _field("title", item.title, MAX_TITLE_LENGTH)
    if not title:
        raise InvalidTextError("title: value must not be empty")
    return CleanText(title, _field("description", item.description, MAX_DESCRIPTION_LENGTH))
