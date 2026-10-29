"""Outcome counts of completed ``llm_extract`` tasks, read from the worker's result notes."""

from __future__ import annotations

from dataclasses import dataclass, fields

from sqlalchemy import ColumnElement, case, func, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus

EXTRACTED_NOTE_PREFIX = "docs="
"""The worker writes ``docs=7 edges=5 dropped=2`` when it staged mentions."""
EMPTY_NOTES = ("no_documents", "login_wall", "no_content")
"""Notes the worker writes verbatim when a page yielded nothing to stage."""


@dataclass(frozen=True, slots=True)
class LlmOutcomeCounts:
    """Completed ``llm_extract`` tasks by what the model run produced."""

    extracted: int
    no_documents: int
    login_wall: int
    no_content: int


def _outcome() -> ColumnElement[str]:
    """Return the SQL expression naming a task's outcome from its note, or ``NULL`` when unrecognised."""
    extracted = DiscoveryTask.result_note.startswith(EXTRACTED_NOTE_PREFIX, autoescape=True)
    return case((extracted, "extracted"), (DiscoveryTask.result_note.in_(EMPTY_NOTES), DiscoveryTask.result_note))


class LlmOutcomeRepository(SessionRepository):
    """Aggregate what the extraction runs produced."""

    def llm_outcome_counts(self) -> LlmOutcomeCounts:
        """Return the completed ``llm_extract`` tasks grouped by result note; unrecognised notes are not counted."""
        outcome = _outcome().label("outcome")
        stmt = (
            select(outcome, func.count())
            .where(
                DiscoveryTask.kind == DiscoveryTaskKind.LLM_EXTRACT,
                DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED,
            )
            .group_by(outcome)
        )
        tally = {name: int(count) for name, count in self._session.execute(stmt).all() if name is not None}
        return LlmOutcomeCounts(
            **{name: tally.get(name, 0) for name in (field.name for field in fields(LlmOutcomeCounts))}
        )
