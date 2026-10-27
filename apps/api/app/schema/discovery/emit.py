"""Result fields shared by every emit route, whatever it emits from."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel


class EmitOutcome(BaseModel):
    """What emitting one item produced: a suggestion, or the reason it was skipped."""

    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    replayed: bool = False


class EmitCounts(BaseModel):
    """Totals of one emit call."""

    created_count: int
    skipped_count: int
    replayed_count: int


def tally_outcomes(outcomes: Sequence[EmitOutcome]) -> EmitCounts:
    """Count the created, skipped and replayed ``outcomes``."""
    skipped = sum(outcome.skip_reason is not None for outcome in outcomes)
    replayed = sum(outcome.skip_reason is None and outcome.replayed for outcome in outcomes)
    return EmitCounts(created_count=len(outcomes) - skipped - replayed, skipped_count=skipped, replayed_count=replayed)
