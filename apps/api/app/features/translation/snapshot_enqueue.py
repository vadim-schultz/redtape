"""Snapshot translation tasks for procedure pages: queued when a mention cites a page, refreshed when a new snapshot arrives.

A page is one translation per target locale (decision D1), queued against the raw artifact sha it is made from. Each
entry point names the locales it covers, and one rule queues them: a locale whose stored translation already matches the
artifact is skipped, and a locale that is stored or queued but stale is re-queued at the retranslation rank.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.page_reads import ProcedurePageReads
from app.features.translation.plan import Classification, EnqueueTotals
from app.features.translation.priority import snapshot_first_priority, snapshot_retranslation_priority
from app.features.translation.snapshot_repository import SnapshotRepository
from app.features.translation.source import SourceRepository, get_phases_for_pages
from app.features.translation.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class PageState:
    """One procedure page as the enqueue reads it.

    ``stored`` maps a locale to the artifact sha its stored translation was made from; a skip marker counts as stored.
    ``open_locales`` are the locales with an open (pending or claimed) task. ``confidences`` holds the card confidence of
    each candidate that mentions the page. ``phase`` is the phase from fair_selection_state, defaulting to 1.
    """

    catalogue_service_id: UUID
    artifact_sha256: str
    stored: Mapping[str, str]
    open_locales: frozenset[str]
    confidences: tuple[float, ...]
    phase: int = 1

    @property
    def has_candidates(self) -> bool:
        """Return whether a candidate mentions the page."""
        return bool(self.confidences)

    @property
    def known_locales(self) -> frozenset[str]:
        """Return the locales the page is translated into or has queued."""
        return frozenset(self.stored) | self.open_locales


LocalesOf = Callable[[PageState], Sequence[str]]
"""The rule an entry point applies: the target locales of a page that it covers."""


def classify(page: PageState, locale: str) -> Classification:
    """Return what ``locale`` of ``page`` needs: nothing when its stored translation matches the artifact."""
    if locale not in page.stored:
        return Classification.MISSING
    return Classification.CURRENT if page.stored[locale] == page.artifact_sha256 else Classification.STALE


def _is_skipped(kind: Classification) -> bool:
    """Return whether a slot of ``kind`` needs no task: its stored translation already matches the artifact."""
    return kind is Classification.CURRENT


def _priority(page: PageState, locale: str) -> int:
    """Rank a first translation by the page's best candidate and phase, and a stale one behind every first translation."""
    if locale in page.stored:
        return snapshot_retranslation_priority(page.confidences, phase=page.phase)
    return snapshot_first_priority(page.confidences, phase=page.phase)


def _scores_of(candidate_ids: Sequence[UUID], scores: Mapping[UUID, float]) -> tuple[float, ...]:
    return tuple(scores[candidate_id] for candidate_id in candidate_ids)


class SnapshotEnqueuer:
    """Queue the snapshot translation of procedure pages into the target locales, one open task per page and locale."""

    def __init__(self, session: Session, locales: Sequence[str] | None = None) -> None:
        """Bind the enqueuer to ``session`` and the target ``locales`` (the configured ones by default)."""
        self._session = session
        self._locales = tuple(settings.translation_target_locale_codes if locales is None else locales)
        self._pages = ProcedurePageReads.for_session(session)
        self._index = SnapshotRepository(session)
        self._tasks = TaskRepository(session)
        self._source = SourceRepository(session)

    def enqueue_pages(self, catalogue_ids: Sequence[UUID]) -> EnqueueTotals:
        """Mention hook: queue every target locale of each page with a snapshot that is not yet current."""
        if not catalogue_ids:
            return EnqueueTotals()
        snapshots = self._pages.latest_snapshots(catalogue_ids)
        return self.queue(self.load({page: snapshot.sha256 for page, snapshot in snapshots.items()}), self.every_locale)

    def snapshot_stored(self, catalogue_service_id: UUID, artifact_sha256: str) -> None:
        """Upload listener: refresh the locales this page is already translated into or has queued, and no other."""
        self.queue(self.load({catalogue_service_id: artifact_sha256}), self.known_locales)

    def pages_after(self, after: UUID | None, limit: int) -> dict[UUID, str]:
        """Backfill: the latest snapshot sha of the next ``limit`` pages that have one, after ``after``, in id order."""
        return {page: snapshot.sha256 for page, snapshot in self._pages.latest_snapshots_after(after, limit).items()}

    def every_locale(self, _page: PageState) -> tuple[str, ...]:
        """Return every target locale, the rule a mention applies."""
        return self._locales

    def known_locales(self, page: PageState) -> tuple[str, ...]:
        """Return the target locales the page is translated into or has queued, the rule a new snapshot applies."""
        return tuple(locale for locale in self._locales if locale in page.known_locales)

    def wanted_locales(self, page: PageState) -> tuple[str, ...]:
        """Return every target locale of a page with candidates and the known ones of any other page, for a backfill."""
        return self._locales if page.has_candidates else self.known_locales(page)

    def load(self, shas: Mapping[UUID, str]) -> list[PageState]:
        """Read each page in ``shas``, which maps a catalogue row to the artifact sha it is translated from."""
        if not shas or not self._locales:
            return []
        pages = list(shas)
        candidates = self._pages.candidate_ids_by_page(pages)
        scores = self._source.confidences_for(sorted({c for ids in candidates.values() for c in ids}))
        stored, open_locales = self._index.stored_shas(pages), self._index.open_locales(pages)
        phases = get_phases_for_pages(self._session, pages)
        return [
            PageState(
                page,
                sha,
                stored.get(page, {}),
                open_locales.get(page, frozenset()),
                _scores_of(candidates.get(page, ()), scores),
                phases.get(page, 1),
            )
            for page, sha in shas.items()
        ]

    def count(self, pages: Sequence[PageState], locales_of: LocalesOf) -> EnqueueTotals:
        """Classify every page and locale the rule names, without writing anything."""
        return EnqueueTotals(counts=Counter(kind for _, _, kind in self._slots(pages, locales_of)))

    def queue(self, pages: Sequence[PageState], locales_of: LocalesOf) -> EnqueueTotals:
        """Queue every page and locale the rule names that is not skipped; a repeat changes nothing."""
        slots = self._slots(pages, locales_of)
        queued = sum(self._upsert(page, locale) for page, locale, kind in slots if not _is_skipped(kind))
        return EnqueueTotals(counts=Counter(kind for _, _, kind in slots), enqueued=queued)

    def _slots(self, pages: Sequence[PageState], locales_of: LocalesOf) -> list[tuple[PageState, str, Classification]]:
        return [(page, locale, classify(page, locale)) for page in pages for locale in locales_of(page)]

    def _upsert(self, page: PageState, locale: str) -> bool:
        return self._tasks.upsert_snapshot_pending(
            (page.catalogue_service_id, locale), page.artifact_sha256, _priority(page, locale)
        )
