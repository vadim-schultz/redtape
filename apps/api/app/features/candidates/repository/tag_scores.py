"""The scored category codes of a page of candidates, loaded in one query from the SQL score model."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery


class ScoredCode(NamedTuple):
    """One canonical category code of a candidate and its score."""

    code: str
    score: float


class TagScoreRepository(SessionRepository):
    """Expose the category-score relation to services."""

    def tag_scores_for(self, candidate_ids: Sequence[UUID]) -> dict[UUID, tuple[ScoredCode, ...]]:
        """Return the scored categories of ``candidate_ids``, best first; ids without a mention are absent."""
        if not candidate_ids:
            return {}
        rel = tag_scores_subquery()
        stmt = select(rel.c.candidate_id, rel.c.code, rel.c.score)
        stmt = stmt.where(rel.c.candidate_id.in_(candidate_ids)).order_by(rel.c.score.desc(), rel.c.code)
        grouped: dict[UUID, list[ScoredCode]] = defaultdict(list)
        for row in self._session.execute(stmt):
            grouped[row.candidate_id].append(ScoredCode(row.code, row.score))
        return {candidate_id: tuple(scores) for candidate_id, scores in grouped.items()}
