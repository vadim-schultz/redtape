"""The base validators: each is a small pure function over ``(source, translated)`` that returns a problem or ``None``.

:func:`validate_text` runs all of them; :func:`validate_unit` runs them over the title and the description of a unit.
"""

from __future__ import annotations

from collections import Counter
from typing import Final, Literal

from discovery_ingest.translation import tokens
from discovery_ingest.translation.findings import Check, Finding
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.units import TranslationUnit
from discovery_ingest.translation.validate_glossary import glossary_adherence

MIN_LENGTH_RATIO: Final = 0.35
MAX_LENGTH_RATIO: Final = 3.5
RATIO_SLACK: Final = 10
"""Added to both lengths so that a two-word title is not rejected for a few characters."""
SHORT_COPY_WORDS: Final = 2
"""A text of at most this many words may come back unchanged (a proper noun or a short name)."""


def _missing(kind: str, needed: Counter[str], present: Counter[str]) -> str | None:
    missing = needed - present
    return f"{kind} not preserved: {', '.join(sorted(missing))}" if missing else None


def non_empty(source: str, translated: str) -> str | None:
    """Reject a vanished translation, and text invented for an empty source."""
    if source.strip() and not translated.strip():
        return "the translation is empty"
    if not source.strip() and translated.strip():
        return "text was invented for an empty source"
    return None


def length_ratio(source: str, translated: str) -> str | None:
    """Reject a stub or a runaway: the translation's length must be within bounds of the source's."""
    ratio = (len(translated) + RATIO_SLACK) / (len(source) + RATIO_SLACK)
    if MIN_LENGTH_RATIO <= ratio <= MAX_LENGTH_RATIO:
        return None
    return f"length ratio {ratio:.2f} outside {MIN_LENGTH_RATIO}..{MAX_LENGTH_RATIO}"


def numbers_preserved(source: str, translated: str) -> str | None:
    """Every number of the source appears as often in the translation (compared by value)."""
    return _missing("numbers", tokens.numbers(source), tokens.numbers(translated))


def dates_preserved(source: str, translated: str) -> str | None:
    """Every numeric date of the source appears exactly as written."""
    return _missing("dates", tokens.dates(source), tokens.dates(translated))


def urls_preserved(source: str, translated: str) -> str | None:
    """Every URL of the source appears exactly as written."""
    return _missing("urls", tokens.urls(source), tokens.urls(translated))


def citations_preserved(source: str, translated: str) -> str | None:
    """Every legal citation of the source (``§ 35``, ``Art. 5``) appears in the translation."""
    return _missing("citations", tokens.citations(source), tokens.citations(translated))


def placeholders_preserved(source: str, translated: str) -> str | None:
    """Require the placeholders of the translation to be exactly those of the source: none dropped, none invented."""
    wanted, found = tokens.placeholders(source), tokens.placeholders(translated)
    return _missing("placeholders", wanted, found) or _missing("extra placeholders", found, wanted)


def no_added_markup(source: str, translated: str) -> str | None:
    """Reject markup in the translation that the source did not have."""
    added = tokens.markup(translated) - tokens.markup(source)
    return f"markup added: {', '.join(sorted(added))}" if added else None


def not_an_unchanged_copy(source: str, translated: str) -> str | None:
    """Reject a text of more than a few words that was returned as it came."""
    if len(source.split()) <= SHORT_COPY_WORDS or source.strip().casefold() != translated.strip().casefold():
        return None
    return "the translation is an unchanged copy of the source"


TOKEN_CHECKS: Final[tuple[tuple[str, Check], ...]] = (
    ("placeholders", placeholders_preserved),
    ("numbers", numbers_preserved),
    ("dates", dates_preserved),
    ("urls", urls_preserved),
    ("citations", citations_preserved),
)
OTHER_CHECKS: Final[tuple[tuple[str, Check], ...]] = (
    ("non_empty", non_empty),
    ("length_ratio", length_ratio),
    ("markup", no_added_markup),
    ("unchanged_copy", not_an_unchanged_copy),
)


def _run(checks: tuple[tuple[str, Check], ...], source: str, translated: str) -> list[Finding]:
    results = ((name, check(source, translated)) for name, check in checks)
    return [Finding(name, "text", detail) for name, detail in results if detail]


def token_findings(source: str, translated: str) -> list[Finding]:
    """Run the checks that compare tokens (placeholders, numbers, dates, URLs, citations)."""
    return _run(TOKEN_CHECKS, source, translated)


def validate_text(source: str, translated: str, glossary: Glossary) -> list[Finding]:
    """Run every check on one text; the findings are empty when the translation keeps every promise."""
    checks = (*OTHER_CHECKS, *TOKEN_CHECKS, ("glossary", glossary_adherence(glossary)))
    return _run(checks, source, translated)


def _tagged(field: Literal["title", "description"], findings: list[Finding]) -> list[Finding]:
    return [Finding(finding.check, field, finding.detail) for finding in findings]


def validate_unit(source: TranslationUnit, translated: TranslationUnit, glossary: Glossary) -> list[Finding]:
    """Validate the title and the description of ``translated`` against ``source``, naming the field of each finding."""
    title = validate_text(source.title, translated.title, glossary)
    description = validate_text(source.description, translated.description, glossary)
    return [*_tagged("title", title), *_tagged("description", description)]
