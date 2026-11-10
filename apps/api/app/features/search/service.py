"""Keep ``candidate_search_text`` current and queue the embedding work its changes need."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.search.enqueue import EmbeddingEnqueuer, EnqueueOutcome
from app.features.search.repository import SearchTextRepository
from app.features.search.results import RefreshResult, RefreshStatus, RefreshTotals
from app.features.search.text import build
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
        outcome = self._enqueuer.enqueue(candidate_id, built)
        return RefreshResult(RefreshStatus.WRITTEN, enqueued=outcome is EnqueueOutcome.QUEUED)

    def refresh_many(self, candidate_ids: Iterable[UUID]) -> RefreshTotals:
        """Refresh every candidate and total the outcomes."""
        totals = RefreshTotals()
        for candidate_id in candidate_ids:
            totals.add(self.refresh(candidate_id))
        return totals
