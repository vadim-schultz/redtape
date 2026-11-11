"""Keep ``candidate_search_text`` current and queue the embedding work its changes need."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.search.enqueue import EmbeddingEnqueuer, EnqueueOutcome
from app.features.search.repository import SearchTextRepository
from app.features.search.results import RefreshResult, RefreshStatus, RefreshTotals
from app.features.search.text import BuiltText, build, build_translated
from app.features.translation.store import TranslationPayload
from app.models.search import CANONICAL_LOCALE


class SearchTextService:
    """Rebuild the canonical text of a candidate; write it and enqueue an embedding only when its hash changed."""

    def __init__(self, repository: SearchTextRepository, enqueuer: EmbeddingEnqueuer) -> None:
        """Bind the service to the text ``repository`` and the task ``enqueuer``."""
        self._repo = repository
        self._enqueuer = enqueuer

    @classmethod
    def for_session(cls, session: Session) -> SearchTextService:
        """Build the service over ``session`` for the configured embedding model."""
        return cls(SearchTextRepository(session), EmbeddingEnqueuer(session, settings.embedding_model))

    def refresh(self, candidate_id: UUID) -> RefreshResult:
        """Refresh the canonical-locale text of one candidate in the caller's transaction."""
        titles = self._repo.candidate_titles(candidate_id) or {}
        built = build(titles, self._repo.mention_excerpts(candidate_id), CANONICAL_LOCALE)
        if built is None:
            return RefreshResult(RefreshStatus.SKIPPED_EMPTY)
        if not self._repo.upsert_search_text(candidate_id, built):
            return RefreshResult(RefreshStatus.UNCHANGED)
        return self._queue(candidate_id, built, RefreshStatus.WRITTEN)

    def refresh_locale(self, candidate_id: UUID, locale: str, payload: TranslationPayload) -> RefreshResult:
        """Refresh the ``locale`` text of one candidate from its stored translation, in the caller's transaction.

        Unlike :meth:`refresh`, an unchanged text still reaches the enqueuer: it decides from the stored embedding,
        so a locale that was pruned and enabled again is queued by a backfill. Raises
        :class:`UnsupportedSearchLocaleError` for a locale that has no translated text.
        """
        built = build_translated(locale, payload.title, payload.description)
        if built is None:
            return RefreshResult(RefreshStatus.SKIPPED_EMPTY)
        written = self._repo.upsert_search_text(candidate_id, built)
        return self._queue(candidate_id, built, RefreshStatus.WRITTEN if written else RefreshStatus.UNCHANGED)

    def _queue(self, candidate_id: UUID, built: BuiltText, status: RefreshStatus) -> RefreshResult:
        outcome = self._enqueuer.enqueue(candidate_id, built)
        return RefreshResult(status, enqueued=outcome is EnqueueOutcome.QUEUED)

    def refresh_many(self, candidate_ids: Iterable[UUID]) -> RefreshTotals:
        """Refresh every candidate and total the outcomes."""
        totals = RefreshTotals()
        for candidate_id in candidate_ids:
            totals.add(self.refresh(candidate_id))
        return totals
