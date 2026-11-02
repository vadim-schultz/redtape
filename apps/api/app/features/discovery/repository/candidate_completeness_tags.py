"""Usable tag codes per candidate: one scoring engine shared by the bulk and single-candidate paths."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import groupby
from uuid import UUID

from sqlalchemy import ColumnElement, Float, Row, cast, distinct, func, or_, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import CTE, Select, Subquery
from sqlalchemy.sql.functions import array_agg

from app.features.discovery.tags import (
    LLM_SCORE_BASE,
    LLM_SCORE_CEILING,
    LLM_SCORE_STEP,
    MANUAL_EXTRACTOR,
    MIN_SUGGESTED_SCORE,
    TagAxis,
    TagSupport,
    llm_evidence_score,
    noisy_or,
)
from app.models.discovery import DiscoveryCandidateMention as Mention


def _confidence_column(axis: TagAxis) -> ColumnElement[float]:
    """Cast the axis' direct-confidence column so it type-checks as a plain float expression."""
    return cast(axis.confidence_column, Float)


def _exploded(axis: TagAxis) -> CTE:
    code = func.unnest(axis.column).label("code")
    confidence = _confidence_column(axis).label("confidence")
    stmt = select(Mention.candidate_id, Mention.catalogue_service_id, Mention.extractor, confidence, code)
    return stmt.cte(f"{axis.value}_exploded")


def _tagged(exploded: CTE) -> Subquery:
    tagged = func.count(distinct(exploded.c.catalogue_service_id))
    return select(exploded.c.candidate_id, tagged.label("tagged")).group_by(exploded.c.candidate_id).subquery()


def _sorted_codes(code: ColumnElement[str]) -> array_agg[str]:
    return func.array_agg(aggregate_order_by(distinct(code), code))


def _llm_score_sql(procedures: ColumnElement[int], share: ColumnElement[float]) -> ColumnElement[float]:
    """Mirror :func:`llm_evidence_score` in SQL, for the bulk path's usability predicate."""
    raw = LLM_SCORE_BASE + LLM_SCORE_STEP * (cast(procedures, Float) - 1)
    capped = func.least(LLM_SCORE_CEILING, raw)
    return func.coalesce(capped * share, 0.0)


def _support_rows(exploded: CTE) -> Subquery:
    """Return one row per ``(candidate_id, code)``: whether any row carries a direct confidence, and the
    distinct procedures of the rows that don't (its LLM-only evidence).
    """
    confidence = exploded.c.confidence
    has_direct = func.bool_or(confidence.is_not(None))
    llm_procedures = func.count(distinct(exploded.c.catalogue_service_id)).filter(confidence.is_(None))
    keys = (exploded.c.candidate_id, exploded.c.code)
    cols = (*keys, has_direct.label("has_direct"), llm_procedures.label("llm_procedures"))
    return select(*cols).group_by(*keys).subquery()


def _usable(support: Subquery, tagged: Subquery) -> ColumnElement[bool]:
    """Whether a code clears the inclusion floor: any direct source, or an LLM-only score above it (D9)."""
    share = cast(cast(support.c.llm_procedures, Float) / cast(tagged.c.tagged, Float), Float)
    llm_score = _llm_score_sql(support.c.llm_procedures, share)
    return or_(support.c.has_direct, llm_score >= MIN_SUGGESTED_SCORE)


def code_support(exploded: CTE) -> Select:
    """Return one row per ``(candidate_id, code)`` with whether it clears the inclusion floor (``usable``).

    Used only by the bulk completeness path — the single-candidate detail path scores codes directly in
    Python (:func:`candidate_axis_support`), where the exact score (not just whether it clears the floor)
    matters.
    """
    support, tagged = _support_rows(exploded), _tagged(exploded)
    joined = support.join(tagged, tagged.c.candidate_id == support.c.candidate_id)
    cols = (support.c.candidate_id, support.c.code)
    return select(*cols, _usable(support, tagged).label("usable")).select_from(joined)


def _consensus(exploded: CTE) -> Select:
    rows = code_support(exploded).subquery()
    stmt = select(rows.c.candidate_id, _sorted_codes(rows.c.code).label("codes"))
    return stmt.where(rows.c.usable).group_by(rows.c.candidate_id)


def _manual_branch(exploded: CTE) -> Select:
    stmt = select(exploded.c.candidate_id, _sorted_codes(exploded.c.code).label("codes"))
    return stmt.where(exploded.c.extractor == MANUAL_EXTRACTOR).group_by(exploded.c.candidate_id)


def _manual_support(exploded: CTE) -> Select:
    """Return one row per ``(candidate_id, code)`` manually asserted, each with its procedure count.

    The per-code mirror of :func:`_manual_branch`, which aggregates the same rows into one codes array.
    """
    procedures = func.count(distinct(exploded.c.catalogue_service_id))
    keys = (exploded.c.candidate_id, exploded.c.code)
    stmt = select(*keys, procedures.label("procedures")).where(exploded.c.extractor == MANUAL_EXTRACTOR)
    return stmt.group_by(*keys)


def _sorted_supports(supports: list[TagSupport]) -> list[TagSupport]:
    return sorted(supports, key=lambda support: (-support.procedures, support.code))


def axis_acceptance(axis: TagAxis) -> Subquery:
    """Return ``(candidate_id, codes)`` for the candidates with usable codes on ``axis``.

    The codes of the manual mentions replace the consensus; ``codes`` is sorted and never empty.
    """
    exploded = _exploded(axis)
    manual = _manual_branch(exploded).subquery()
    consensus = _consensus(exploded).subquery()
    joined = manual.join(consensus, manual.c.candidate_id == consensus.c.candidate_id, full=True)
    candidate_id = func.coalesce(manual.c.candidate_id, consensus.c.candidate_id)
    codes = func.coalesce(manual.c.codes, consensus.c.codes)
    return select(candidate_id.label("candidate_id"), codes.label("codes")).select_from(joined).subquery()


def _candidate_rows(axis: TagAxis, candidate_id: UUID) -> Select:
    code = func.unnest(axis.column).label("code")
    confidence = _confidence_column(axis).label("confidence")
    cols = (Mention.catalogue_service_id, code, confidence)
    return select(*cols).where(Mention.candidate_id == candidate_id)


def _distinct_procedures(rows: Sequence[Row]) -> int:
    return len({row.catalogue_service_id for row in rows})


def _group_by_code(rows: Sequence[Row]) -> list[tuple[str, list[Row]]]:
    ordered = sorted(rows, key=lambda row: row.code)
    return [(code, list(code_rows)) for code, code_rows in groupby(ordered, key=lambda row: row.code)]


def _score_rows(rows: Sequence[Row], total_tagged: int) -> list[TagSupport]:
    """Score every code of ``rows`` by combining its LLM evidence and any direct confidence via noisy-OR."""
    supports = []
    for code, code_rows in _group_by_code(rows):
        llm_rows = [r for r in code_rows if r.confidence is None]
        direct = [r.confidence for r in code_rows if r.confidence is not None]
        llm_procedures = _distinct_procedures(llm_rows)
        llm_share = llm_procedures / total_tagged if total_tagged else 0.0
        llm_score = llm_evidence_score(llm_procedures, llm_share)
        procedures = _distinct_procedures(code_rows)
        share = procedures / total_tagged if total_tagged else 0.0
        supports.append(TagSupport(code, procedures, share, noisy_or([llm_score, *direct])))
    return supports


def _leaf_code_rows(candidate_id: UUID) -> Select:
    code = func.unnest(Mention.situation_codes).label("code")
    cols = (code, Mention.pvog_leaf_code.label("leaf_code"))
    return select(*cols).where(Mention.candidate_id == candidate_id, Mention.pvog_leaf_code.is_not(None))


def candidate_situation_leaf_codes(session: Session, candidate_id: UUID) -> dict[str, str]:
    """Return the PVOG leaf code behind each situation code any of ``candidate_id``'s mentions assert.

    When more than one PVOG mention asserts the same code with a different leaf — rare, not observed in
    production per the prior suite's near-zero PVOG/LLM overlap finding — the lexicographically first
    leaf code wins, deterministically, rather than an arbitrary one.
    """
    rows = session.execute(_leaf_code_rows(candidate_id)).all()
    by_code: dict[str, list[str]] = {}
    for row in rows:
        by_code.setdefault(row.code, []).append(row.leaf_code)
    return {code: min(leaves) for code, leaves in by_code.items()}


def candidate_axis_support(session: Session, candidate_id: UUID, axis: TagAxis) -> list[TagSupport]:
    """Return the score of every code of one candidate's mentions on ``axis``, most supported first.

    A manual mention replaces the consensus entirely for the axis, the same way :func:`axis_acceptance`
    replaces it for the bulk path — its codes score ``1.0``, a full curator override.
    """
    exploded = _exploded(axis)
    manual_stmt = _manual_support(exploded).where(exploded.c.candidate_id == candidate_id)
    manual_rows = session.execute(manual_stmt).all()
    if manual_rows:
        return _sorted_supports([TagSupport(row.code, row.procedures, 1.0, 1.0) for row in manual_rows])
    rows = session.execute(_candidate_rows(axis, candidate_id)).all()
    return _sorted_supports(_score_rows(rows, _distinct_procedures(rows)))
