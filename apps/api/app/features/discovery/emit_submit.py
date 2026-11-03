"""Submit a suggestion from either emit flow, turning suggestion-rule failures into skips."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.suggestions.service import (
    CycleError,
    DuplicateSuggestionError,
    MissingSourceUrlError,
    SubmissionResult,
    SuggestionService,
    UnknownDocumentError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submitters import Submitter
from app.schema.discovery.emit import SkipReason
from app.schema.suggestion.create import SuggestionCreate

SUGGESTION_RULE_REASONS: dict[type[Exception], SkipReason] = {
    UnknownTaxonomyCodeError: SkipReason.INVALID_PAYLOAD,
    UnknownDocumentError: SkipReason.INVALID_PAYLOAD,
    CycleError: SkipReason.INVALID_PAYLOAD,
    MissingSourceUrlError: SkipReason.NO_SOURCE_URL,
}


def submit_or_skip(
    suggestions: SuggestionService, *, submitter: Submitter, request: SuggestionCreate, idempotency_key: str
) -> SubmissionResult:
    """Create the suggestion, or raise ``EmitSkip`` when the suggestion rules reject this one item."""
    try:
        return suggestions.create(submitter=submitter, request=request, idempotency_key=idempotency_key)
    except DuplicateSuggestionError as exc:
        raise EmitSkip(SkipReason.DUPLICATE, exc.conflicts) from exc
    except (UnknownTaxonomyCodeError, UnknownDocumentError, CycleError, MissingSourceUrlError) as exc:
        raise EmitSkip(SUGGESTION_RULE_REASONS[type(exc)]) from exc


def idempotency_key(kind: str, item_id: UUID) -> str:
    """Return the key under which ``item_id`` of ``kind`` is submitted, so a replay finds its suggestion."""
    return f"discovery-{kind}:{item_id}"
