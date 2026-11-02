"""The scored tags of a page of candidates, loaded in one query from the SQL score model."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import Row, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery
from app.features.discovery.tags import TagAxis


class ScoredCode(NamedTuple):
    """One taxonomy code of a candidate and its score."""

    code: str
    score: float


class CandidateTagScores(NamedTuple):
    """Every scored code of one candidate per axis, most confident first."""

    domains: tuple[ScoredCode, ...] = ()
    situations: tuple[ScoredCode, ...] = ()


def _by_candidate(rows: Iterable[Row]) -> dict[UUID, CandidateTagScores]:
    """Group score-ordered ``(candidate_id, axis, code, score)`` rows by candidate and axis."""
    grouped: dict[UUID, dict[str, list[ScoredCode]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row.candidate_id][row.axis].append(ScoredCode(row.code, row.score))
    return {
        candidate_id: CandidateTagScores(tuple(axes[TagAxis.DOMAIN.value]), tuple(axes[TagAxis.SITUATION.value]))
        for candidate_id, axes in grouped.items()
    }


class TagScoreRepository(SessionRepository):
    """Expose the tag-score relation to services."""

    def tag_scores_for(self, candidate_ids: Sequence[UUID]) -> dict[UUID, CandidateTagScores]:
        """Return the scored tags of ``candidate_ids``; ids without a mention are absent."""
        if not candidate_ids:
            return {}
        rel = tag_scores_subquery()
        stmt = select(rel.c.candidate_id, rel.c.axis, rel.c.code, rel.c.score)
        stmt = stmt.where(rel.c.candidate_id.in_(candidate_ids)).order_by(rel.c.score.desc(), rel.c.code)
        return _by_candidate(self._session.execute(stmt))
