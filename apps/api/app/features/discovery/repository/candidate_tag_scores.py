"""The category score of every ``(candidate, code)`` in SQL: the bulk mirror of :func:`candidate_category_support`.

Unlike the usability predicate of :func:`code_support`, this relation applies no inclusion floor: a code
with at least one mention has a row. A manual mention replaces the consensus at score ``1.0``;
otherwise the LLM-evidence score and any direct confidences combine by noisy-OR, in log space.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, literal, select, union_all
from sqlalchemy.sql.expression import CTE, Select, Subquery

from app.features.discovery.repository.candidate_completeness_tags import (
    NOISY_OR_CLAMP,
    exploded_categories,
    llm_score_of,
    manual_support,
    support_rows,
    tagged_procedures,
)

MANUAL_SCORE = 1.0
SCORES_CTE = "scored"
"""CTE name suffix of this relation, so it can share a query with the completeness read model."""


def _noisy_or_sql(llm_score: ColumnElement[float], direct_log: ColumnElement[float]) -> ColumnElement[float]:
    """Mirror :func:`noisy_or` over ``[llm_score, *direct]``: ``1 - exp(sum(ln(1 - s)))``."""
    llm_log = func.ln(1 - func.least(llm_score, 1 - NOISY_OR_CLAMP))
    return 1 - func.exp(llm_log + direct_log)


def _consensus_scores(exploded: CTE) -> Select:
    """Return ``(candidate_id, code, score)`` for every code of every candidate, ignoring manual mentions."""
    support, tagged = support_rows(exploded), tagged_procedures(exploded)
    joined = support.join(tagged, tagged.c.candidate_id == support.c.candidate_id)
    score = _noisy_or_sql(llm_score_of(support, tagged), support.c.direct_log)
    return select(support.c.candidate_id, support.c.code, score.label("score")).select_from(joined)


def _manual_scores(exploded: CTE) -> Select:
    """Return ``(candidate_id, code, score)`` for the manually asserted codes, each at :data:`MANUAL_SCORE`."""
    manual = manual_support(exploded).subquery()
    return select(manual.c.candidate_id, manual.c.code, literal(MANUAL_SCORE).label("score"))


def tag_scores_subquery() -> Subquery:
    """Return ``(candidate_id, code, score)`` for every canonical category code of every candidate.

    Manual codes replace a candidate's consensus, so a candidate with a manual mention keeps only its manual codes.
    """
    exploded = exploded_categories(SCORES_CTE)
    manual, consensus = _manual_scores(exploded).subquery(), _consensus_scores(exploded).subquery()
    kept = select(consensus).where(consensus.c.candidate_id.not_in(select(manual.c.candidate_id)))
    return union_all(select(manual), kept).subquery()
