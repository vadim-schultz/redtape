"""The exact tag scores of one candidate, computed in Python: the single-candidate mirror of the SQL score model."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import groupby
from uuid import UUID

from sqlalchemy import Row, Select, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import CTE

from app.features.discovery.repository.candidate_completeness_tags import exploded_codes, manual_support
from app.features.discovery.tags import TagAxis, TagSupport, llm_evidence_score, noisy_or


def _mention_rows(exploded: CTE, candidate_id: UUID) -> Select:
    cols = (exploded.c.catalogue_service_id, exploded.c.code, exploded.c.confidence)
    return select(*cols).where(exploded.c.candidate_id == candidate_id)


def _distinct_procedures(rows: Sequence[Row]) -> int:
    return len({row.catalogue_service_id for row in rows})


def _group_by_code(rows: Sequence[Row]) -> list[tuple[str, list[Row]]]:
    ordered = sorted(rows, key=lambda row: row.code)
    return [(code, list(code_rows)) for code, code_rows in groupby(ordered, key=lambda row: row.code)]


def _score_code(code: str, code_rows: Sequence[Row], total_tagged: int) -> TagSupport:
    """Score one code: its LLM evidence and any direct confidence combined via noisy-OR."""
    llm_rows = [row for row in code_rows if row.confidence is None]
    direct = [row.confidence for row in code_rows if row.confidence is not None]
    llm_procedures = _distinct_procedures(llm_rows)
    llm_share = llm_procedures / total_tagged if total_tagged else 0.0
    procedures = _distinct_procedures(code_rows)
    share = procedures / total_tagged if total_tagged else 0.0
    return TagSupport(code, procedures, share, noisy_or([llm_evidence_score(llm_procedures, llm_share), *direct]))


def _score_rows(rows: Sequence[Row], total_tagged: int) -> list[TagSupport]:
    """Score every code of ``rows``."""
    return [_score_code(code, code_rows, total_tagged) for code, code_rows in _group_by_code(rows)]


def _sorted_supports(supports: list[TagSupport]) -> list[TagSupport]:
    return sorted(supports, key=lambda support: (-support.procedures, support.code))


def candidate_axis_support(session: Session, candidate_id: UUID, axis: TagAxis) -> list[TagSupport]:
    """Return the score of every code of one candidate's mentions on ``axis``, most supported first.

    A manual mention replaces the consensus entirely for the axis, the same way :func:`axis_acceptance`
    replaces it for the bulk path — its codes score ``1.0``, a full curator override.
    """
    exploded = exploded_codes(axis)
    manual_stmt = manual_support(exploded).where(exploded.c.candidate_id == candidate_id)
    manual_rows = session.execute(manual_stmt).all()
    if manual_rows:
        return _sorted_supports([TagSupport(row.code, row.procedures, 1.0, 1.0) for row in manual_rows])
    rows = session.execute(_mention_rows(exploded, candidate_id)).all()
    return _sorted_supports(_score_rows(rows, _distinct_procedures(rows)))
