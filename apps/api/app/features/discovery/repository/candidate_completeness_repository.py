"""Read the completeness of chosen candidates."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_completeness import (
    CandidateCompleteness,
    TagThresholds,
    completeness_columns,
    completeness_subquery,
)


class CompletenessRepository(SessionRepository):
    """Expose the completeness read model to services."""

    def completeness_for(self, candidate_ids: Sequence[UUID]) -> dict[UUID, CandidateCompleteness]:
        """Return the completeness of ``candidate_ids``, keyed by candidate id, with the settings thresholds."""
        if not candidate_ids:
            return {}
        sub = completeness_subquery(TagThresholds.from_settings(settings))
        stmt = select(*completeness_columns(sub)).where(sub.c.candidate_id.in_(candidate_ids))
        values = (CandidateCompleteness.from_row(row) for row in self._session.execute(stmt))
        return {value.candidate_id: value for value in values}
