"""The strings to translate: one per interface key and per category name and description."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from discovery_ingest.translation.units import TranslationUnit

TAXONOMY_PREFIX = "taxonomy:"
TAXONOMY_FIELDS = ("name", "description")
CATEGORY_NOTES = {
    "name": "the name of a document category, shown as a short label on a filter chip",
    "description": "the one-sentence description of a document category",
}


@dataclass(frozen=True, slots=True)
class SourceString:
    """A string to translate: its ``key``, the German and the English source and a ``note`` for the model."""

    key: str
    german: str
    english: str
    note: str = ""

    def unit(self) -> TranslationUnit:
        """Return the unit the engine translates: German as the text, the key path, English and the note as context."""
        parts = [f"key: {self.key}", f"English: {self.english}", *([self.note] if self.note else [])]
        return TranslationUnit(self.key, self.german, "", "; ".join(parts))


def taxonomy_key(code: str, field: str) -> str:
    """Return the key of a category's ``name`` or ``description``: ``taxonomy:<code>:<field>``."""
    return f"{TAXONOMY_PREFIX}{code}:{field}"


def parse_taxonomy_key(key: str) -> tuple[str, str] | None:
    """Return ``(code, field)`` for a category key, or ``None`` for an interface key."""
    if not key.startswith(TAXONOMY_PREFIX):
        return None
    code, _, field = key.removeprefix(TAXONOMY_PREFIX).rpartition(":")
    return (code, field) if code and field in TAXONOMY_FIELDS else None


def ui_strings(english: Mapping[str, str], german: Mapping[str, str]) -> list[SourceString]:
    """Pair the interface keys of the two source files, sorted; a key only one of them has raises :class:`ValueError`."""
    odd = sorted(set(english) ^ set(german))
    if odd:
        raise ValueError(f"the English and German files differ in keys: {', '.join(odd)}")
    return [SourceString(key, german[key], english[key]) for key in sorted(english)]


def category_strings(code: str, english: Mapping[str, str], german: Mapping[str, str]) -> list[SourceString]:
    """Return the name and description strings of one category; ``english`` and ``german`` map field to text."""
    return [
        SourceString(taxonomy_key(code, field), german[field], english[field], CATEGORY_NOTES[field])
        for field in TAXONOMY_FIELDS
    ]
