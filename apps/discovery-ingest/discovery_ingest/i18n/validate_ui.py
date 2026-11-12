"""The interface-string validators: pure functions over the English source and a translation.

The core's checks (placeholders, numbers, markup, glossary, length against the German) run in
:mod:`discovery_ingest.translation.validate`; the checks here add what only an interface string needs.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Final

from discovery_ingest.i18n.plural import categories_of, family_bases
from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.translation import tokens
from discovery_ingest.translation.findings import Check, Finding

MIN_LAYOUT_RATIO: Final = 0.4
MAX_LAYOUT_RATIO: Final = 2.5
LAYOUT_SLACK: Final = 8
"""Added to both lengths so that a one-word label is not rejected for a few characters."""
LETTERS: Final = re.compile(r"[^\W\d_]")


def _has_words(text: str) -> bool:
    return LETTERS.search(tokens.PLACEHOLDER.sub("", text)) is not None


def untranslated_copy(english: str, allow: frozenset[str]) -> Check:
    """Return the check that a translation is not the English source copied back.

    Text without a word in it (only placeholders or symbols) and sources on the allow list (brand names) may stay.
    """

    def check(_source: str, translated: str) -> str | None:
        if english in allow or not _has_words(english):
            return None
        if translated.strip().casefold() != english.strip().casefold():
            return None
        return "the translation is an untranslated copy of the English text"

    return check


def layout_length(english: str) -> Check:
    """Return the check that a translation's length is within a sane ratio of the English text's (a layout guard)."""

    def check(_source: str, translated: str) -> str | None:
        ratio = (len(translated) + LAYOUT_SLACK) / (len(english) + LAYOUT_SLACK)
        if MIN_LAYOUT_RATIO <= ratio <= MAX_LAYOUT_RATIO:
            return None
        return f"length ratio to the English text {ratio:.2f} outside {MIN_LAYOUT_RATIO}..{MAX_LAYOUT_RATIO}"

    return check


def interface_findings(string: SourceString, translated: str, allow: frozenset[str]) -> list[Finding]:
    """Run the checks only an interface string needs, against the English text; empty when the translation is fine."""
    checks = (
        ("untranslated_english", untranslated_copy(string.english, allow)),
        ("layout", layout_length(string.english)),
    )
    results = ((name, check(string.german, translated)) for name, check in checks)
    return [Finding(name, "text", detail) for name, detail in results if detail]


def indistinct_slavic_families(flat: Mapping[str, str]) -> list[str]:
    """Return the plural families of ``flat`` whose ``few`` and ``many`` forms are the same text, sorted.

    A form that is the same for both counts is not inflected for its count (the nominative-everywhere defect).
    """
    return sorted(
        base
        for base in family_bases(flat)
        if f"{base}_few" in flat and f"{base}_many" in flat and flat[f"{base}_few"] == flat[f"{base}_many"]
    )


def plural_forms_complete(locale: str, keys: Iterable[str]) -> list[str]:
    """Return the keys of the plural forms ``locale`` needs and ``keys`` lack, sorted; empty when every family is whole."""
    present = set(keys)
    needed = (f"{base}_{category}" for base in family_bases(present) for category in categories_of(locale))
    return sorted(key for key in needed if key not in present)
