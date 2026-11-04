"""The PVOG leaf code behind each situation code a candidate's mentions assert."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select, union_all
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.selectable import CompoundSelect

from app.models.discovery import DiscoveryCandidateMention as Mention


def _leaf_code_rows(
    candidate_id: UUID, *code_columns: InstrumentedAttribute[list[str] | None]
) -> Select | CompoundSelect:
    """Return category/legacy code rows with a non-null PVOG leaf."""
    statements = [
        select(func.unnest(column).label("code"), Mention.pvog_leaf_code.label("leaf_code")).where(
            Mention.candidate_id == candidate_id, Mention.pvog_leaf_code.is_not(None)
        )
        for column in code_columns
    ]
    return union_all(*statements)


def _leaf_codes(session: Session, statement: Select | CompoundSelect) -> dict[str, str]:
    """Choose the deterministic first PVOG leaf for each code."""
    rows = session.execute(statement).all()
    by_code: dict[str, list[str]] = {}
    for row in rows:
        by_code.setdefault(row.code, []).append(row.leaf_code)
    return {code: min(leaves) for code, leaves in by_code.items()}


def candidate_situation_leaf_codes(session: Session, candidate_id: UUID) -> dict[str, str]:
    """Return the PVOG leaf code behind each situation code any of ``candidate_id``'s mentions assert.

    When more than one PVOG mention asserts the same code with a different leaf — rare, not observed in
    production per the prior suite's near-zero PVOG/LLM overlap finding — the lexicographically first
    leaf code wins, deterministically, rather than an arbitrary one.
    """
    return _leaf_codes(session, _leaf_code_rows(candidate_id, Mention.situation_codes))


def candidate_category_leaf_codes(session: Session, candidate_id: UUID) -> dict[str, str]:
    """Return the PVOG leaf behind each canonical category a candidate's mentions assert."""
    return _leaf_codes(session, _leaf_code_rows(candidate_id, Mention.domain_codes, Mention.situation_codes))
