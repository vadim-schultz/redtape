"""The PVOG leaf code behind each canonical category a candidate's mentions assert."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.discovery import DiscoveryCandidateMention as Mention


def _leaf_codes(session: Session, statement: Select) -> dict[str, str]:
    """Choose the deterministic first PVOG leaf for each code."""
    rows = session.execute(statement).all()
    by_code: dict[str, list[str]] = {}
    for row in rows:
        by_code.setdefault(row.code, []).append(row.leaf_code)
    return {code: min(leaves) for code, leaves in by_code.items()}


def candidate_category_leaf_codes(session: Session, candidate_id: UUID) -> dict[str, str]:
    """Return the PVOG leaf behind each canonical category a candidate's PVOG mentions assert.

    When more than one PVOG mention asserts the same category with a different leaf, the lexicographically
    first leaf code wins, deterministically, rather than an arbitrary one.
    """
    statement = select(func.unnest(Mention.category_codes).label("code"), Mention.pvog_leaf_code.label("leaf_code"))
    return _leaf_codes(
        session, statement.where(Mention.candidate_id == candidate_id, Mention.pvog_leaf_code.is_not(None))
    )
