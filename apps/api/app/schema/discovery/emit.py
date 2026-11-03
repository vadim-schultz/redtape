"""Result fields shared by every emit route, whatever it emits from."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel


class SkipReason(enum.StrEnum):
    """Why an emit item (claim or candidate) was not turned into a suggestion."""

    NOT_FOUND = "not_found"
    NO_MENTIONS = "no_mentions"
    NO_SOURCE_URL = "no_source_url"
    INVALID_PAYLOAD = "invalid_payload"
    DUPLICATE = "duplicate"
    ALREADY_EMITTED = "already_emitted"
    MISSING_ENTITY = "missing_entity"
    METADATA_NOT_EMITTED = "metadata_not_emitted"
    INVALID_NEW_DOCUMENT_PAYLOAD = "invalid_new_document_payload"
    UNRESOLVED_REQUIREMENT_DOCUMENTS = "unresolved_requirement_documents"


class EmitOutcome(BaseModel):
    """What emitting one item produced: a suggestion, or the reason it was skipped."""

    suggestion_id: UUID | None = None
    skip_reason: SkipReason | None = None
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
