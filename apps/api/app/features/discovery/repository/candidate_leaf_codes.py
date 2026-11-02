"""The PVOG leaf code behind each situation code a candidate's mentions assert."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.discovery import DiscoveryCandidateMention as Mention


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
