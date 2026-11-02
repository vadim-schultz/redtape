"""The best score of every candidate among the selected codes: one grouped pass over the tag-score relation.

A correlated ``EXISTS`` or scalar subquery per candidate re-scans the relation for every row (about 70 times slower
on 4000 candidates: 25 s against 0.35 s), so presence and confidence both read this relation, joined once by candidate.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.tags import TagAxis

Selected = tuple[tuple[TagAxis, tuple[str, ...]], ...]
BEST = "best"


def axis_best(axis: TagAxis) -> str:
    """Return the column name of the best score on ``axis``."""
    return f"{axis.value}_{BEST}"


def _coded(scores: Subquery, axis: TagAxis, codes: tuple[str, ...]) -> ColumnElement[bool]:
    """Return a predicate on a score row: it is on ``axis`` and carries any of ``codes``."""
    return and_(scores.c.axis == axis.value, scores.c.code.in_(codes))


def _within(scores: Subquery, selected: Selected) -> list[ColumnElement[bool]]:
    """Return the restriction of score rows to the selected codes of each axis; none when nothing is selected."""
    return [or_(*(_coded(scores, axis, codes) for axis, codes in selected))] if selected else []


def best_scores(scores: Subquery, selected: Selected) -> Subquery:
    """Return ``(candidate_id, best, <axis>_best ...)``: one row per candidate with a score in the selection.

    With nothing selected every score counts and ``best`` is the candidate's best tag. With codes selected only
    their rows count: ``best`` is the highest of them, and ``<axis>_best`` of each selected axis is ``NULL``
    unless the candidate carries one of that axis' codes, so a non-``NULL`` value is the presence test.
    """
    best = func.max(scores.c.score)
    per_axis = [best.filter(_coded(scores, axis, codes)).label(axis_best(axis)) for axis, codes in selected]
    stmt = select(scores.c.candidate_id, best.label(BEST), *per_axis).group_by(scores.c.candidate_id)
    return stmt.where(*_within(scores, selected)).subquery()
