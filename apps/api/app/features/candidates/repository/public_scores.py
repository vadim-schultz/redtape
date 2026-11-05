"""The best category score of every candidate among the selected codes: one grouped pass over the score relation.

A correlated ``EXISTS`` or scalar subquery per candidate re-scans the relation for every row (about 70 times slower
on 4000 candidates: 25 s against 0.35 s), so presence and confidence both read this relation, joined once by candidate.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.sql.expression import Subquery

BEST = "best"


def _within(scores: Subquery, codes: tuple[str, ...]) -> list[ColumnElement[bool]]:
    """Return the restriction of score rows to the selected codes; none when nothing is selected."""
    return [scores.c.code.in_(codes)] if codes else []


def best_scores(scores: Subquery, codes: tuple[str, ...]) -> Subquery:
    """Return ``(candidate_id, best)``: one row per candidate with a score among ``codes``, or among all when none.

    With nothing selected every score counts and ``best`` is the candidate's best category. With codes selected
    only their rows count, so a non-``NULL`` ``best`` is the presence test.
    """
    best = func.max(scores.c.score).label(BEST)
    stmt = select(scores.c.candidate_id, best).group_by(scores.c.candidate_id)
    return stmt.where(*_within(scores, codes)).subquery()
