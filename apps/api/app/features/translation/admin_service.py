"""The translation admin coverage: the repositories' counts of every target locale, shaped for the route."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.features.search.clock import Clock, utc_now
from app.features.translation.admin_read import Denominators, coverage_of
from app.features.translation.repository import TranslationRepository
from app.features.translation.snapshot_repository import SnapshotRepository
from app.schema.translation.admin import TranslationCoverageResponse


class TranslationAdminService:
    """Count the card and snapshot translations of each target locale without leasing, writing or enqueuing anything."""

    def __init__(self, session: Session, clock: Clock = utc_now) -> None:
        """Bind the service to ``session``; ``clock`` supplies the time that decides which pending tasks are ready."""
        self._index = TranslationRepository(session)
        self._snapshots = SnapshotRepository(session)
        self._clock = clock

    def coverage(self) -> TranslationCoverageResponse:
        """Return the coverage of every configured target locale, and the candidates and pages it is counted against."""
        locales, now = settings.translation_target_locale_codes, self._clock()
        cards = self._index.summary(locales, now)
        snapshots = self._snapshots.summary(locales, now)
        denominators = Denominators(self._index.german_candidate_count(), self._index.snapshot_page_count())
        return coverage_of(cards, snapshots, denominators)
