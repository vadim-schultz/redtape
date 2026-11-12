"""Read model of the translation admin coverage: the repository's per-locale counts shaped for the route."""

from __future__ import annotations

from collections.abc import Sequence

from app.schema.translation.admin import TranslationCoverageResponse, TranslationLocaleCoverage
from app.schema.translation.machine import TranslationLocaleSummary


def coverage_of(summaries: Sequence[TranslationLocaleSummary], denominator: int) -> TranslationCoverageResponse:
    """Shape the counts of each locale, in the order given, with the candidates they are counted against."""
    return TranslationCoverageResponse(denominator=denominator, locales=[_locale_of(each) for each in summaries])


def _locale_of(summary: TranslationLocaleSummary) -> TranslationLocaleCoverage:
    return TranslationLocaleCoverage(
        locale=summary.locale,
        translated=summary.translated,
        stale=summary.stale,
        pending=summary.pending_ready,
        claimed=summary.claimed,
        failed=summary.failed,
    )
