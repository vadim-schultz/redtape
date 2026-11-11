"""The translation summary of a card: whether a stored translation exists for the request locale, and its freshness."""

from __future__ import annotations

from app.features.candidates.repository import TranslationIndexRow
from app.features.translation.unit import TranslationUnit
from app.schema.candidate import CandidateTranslationSummary


def translation_summary(row: TranslationIndexRow | None, unit: TranslationUnit) -> CandidateTranslationSummary | None:
    """Return the summary of the translation at ``row`` measured against the current German ``unit``, or ``None``."""
    if row is None:
        return None
    return CandidateTranslationSummary(locale=row.locale, source=row.source, stale=unit.is_stale(row.source_hash))
