"""Read model of the translation admin coverage: the repositories' per-locale counts shaped for the route."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from app.schema.translation.admin import SnapshotLocaleCoverage, TranslationCoverageResponse, TranslationLocaleCoverage
from app.schema.translation.machine import TranslationLocaleSummary
from app.schema.translation.snapshot_machine import SnapshotLocaleSummary


class Denominators(NamedTuple):
    """What the counts are measured against: candidates with a German card, and procedure pages with a snapshot."""

    cards: int
    snapshots: int


def coverage_of(
    summaries: Sequence[TranslationLocaleSummary],
    snapshots: Sequence[SnapshotLocaleSummary],
    denominators: Denominators,
) -> TranslationCoverageResponse:
    """Shape the counts of each locale, in the order given, with the candidates and pages they are counted against."""
    by_locale = {each.locale: each for each in snapshots}
    return TranslationCoverageResponse(
        denominator=denominators.cards,
        snapshot_denominator=denominators.snapshots,
        locales=[_locale_of(each, by_locale[each.locale]) for each in summaries],
    )


def _locale_of(summary: TranslationLocaleSummary, snapshot: SnapshotLocaleSummary) -> TranslationLocaleCoverage:
    return TranslationLocaleCoverage(
        locale=summary.locale,
        translated=summary.translated,
        stale=summary.stale,
        pending=summary.pending_ready,
        claimed=summary.claimed,
        failed=summary.failed,
        snapshot=_snapshot_of(snapshot),
    )


def _snapshot_of(summary: SnapshotLocaleSummary) -> SnapshotLocaleCoverage:
    return SnapshotLocaleCoverage(
        translated=summary.translated,
        skipped=summary.skipped,
        stale=summary.stale,
        pending=summary.pending_ready,
        failed=summary.failed,
    )
