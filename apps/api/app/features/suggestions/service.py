"""Domain logic for creating and reading suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.documents.promotion import PromotionPort
from app.features.events.service import EventLogService
from app.features.suggestions.filters import SuggestionFilters
from app.features.suggestions.handlers import (
    Conflict,
    CycleError,
    Dispatch,
    HandlerDeps,
    PromotionConflictError,
    UnknownDocumentError,
    UnknownTaxonomyCodeError,
    build_dispatch,
)
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.submitters import MissingSourceUrlError, Submitter
from app.features.suggestions.transitions import AlreadyDecidedError, SuggestionNotFoundError, SuggestionTransitions
from app.features.taxonomy.service import TaxonomyService
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.read import SuggestionListResponse, SuggestionRead

__all__ = [
    "AlreadyDecidedError",
    "Conflict",
    "CycleError",
    "DuplicateSuggestionError",
    "MissingSourceUrlError",
    "PromotionConflictError",
    "SubmissionResult",
    "SuggestionFilters",
    "SuggestionNotFoundError",
    "SuggestionService",
    "UnknownDocumentError",
    "UnknownJurisdictionError",
    "UnknownTaxonomyCodeError",
]


class UnknownJurisdictionError(ValueError):
    """Raised when neither the jurisdiction id nor the municipality code resolves."""


class DuplicateSuggestionError(ValueError):
    """Raised when a suggestion matches existing catalogue entities or pending suggestions."""

    def __init__(self, conflicts: list[Conflict]) -> None:
        super().__init__(f"duplicate suggestion: {len(conflicts)} conflict(s)")
        self.conflicts = conflicts


@dataclass(frozen=True)
class SubmissionResult:
    """Outcome of `SuggestionService.create`: the row, and whether it's an idempotent replay (D8)."""

    suggestion: Suggestion
    replayed: bool


class SuggestionService:
    """Create, read and transition suggestions; per-kind rules live behind the kind dispatch."""

    def __init__(
        self,
        repository: SuggestionRepository,
        documents: PromotionPort,
        taxonomy: TaxonomyService,
        events: EventLogService,
    ) -> None:
        self._repo = repository
        self._documents = documents
        self._events = events
        self._handlers = build_dispatch(HandlerDeps(documents, taxonomy, repository))
        self._transitions = SuggestionTransitions(repository, self._handlers, events)

    def create(
        self, *, submitter: Submitter, request: SuggestionCreate, idempotency_key: str | None = None
    ) -> SubmissionResult:
        """Store a pending suggestion, or return the earlier one that a replayed idempotency key names."""
        if (existing := submitter.find_replay(self._repo, idempotency_key)) is not None:
            return SubmissionResult(existing, replayed=True)
        handler = self._handlers[request.kind]
        jurisdiction_id = self._resolve_jurisdiction(request)
        handler.validate(request.payload, jurisdiction_id=jurisdiction_id)
        submitter.check_source_url(request.source_url)
        self._check_duplicates(handler, jurisdiction_id, request)
        row = self._build_row(submitter, request, jurisdiction_id, idempotency_key, handler)
        return self._insert(row, submitter, idempotency_key)

    def preview_conflicts(self, request: SuggestionCreate) -> list[Conflict]:
        """Validate ``request`` and return what creating it would duplicate; never writes."""
        handler = self._handlers[request.kind]
        jurisdiction_id = self._resolve_jurisdiction(request)
        handler.validate(request.payload, jurisdiction_id=jurisdiction_id)
        return handler.conflicts(request.payload, jurisdiction_id=jurisdiction_id)

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        """Return the suggestion row, or None; the voting feature reads through this rather than the repository."""
        return self._repo.get(suggestion_id)

    def list_suggestions(self, *, filters: SuggestionFilters, offset: int, limit: int) -> SuggestionListResponse:
        """Return one page of suggestions matching ``filters``."""
        total = self._repo.count(filters)
        rows = self._repo.list_page(filters, offset=offset, limit=limit)
        items = [SuggestionRead.from_row(row, submitter_display_name=name) for row, name in rows]
        return SuggestionListResponse(items=items, total=total, offset=offset, limit=limit)

    def get_suggestion(self, suggestion_id: UUID) -> SuggestionRead | None:
        """Return one suggestion with its submitter's display name, or None."""
        found = self._repo.get_with_submitter(suggestion_id)
        if found is None:
            return None
        suggestion, name = found
        return SuggestionRead.from_row(suggestion, submitter_display_name=name)

    def transition_to(self, suggestion_id: UUID, new_status: SuggestionStatus, actor: AppUser | None) -> Suggestion:
        """Delegate to `SuggestionTransitions`, the one place `status` changes (D5)."""
        return self._transitions.transition_to(suggestion_id, new_status, actor)

    def _insert(self, row: Suggestion, submitter: Submitter, idempotency_key: str | None) -> SubmissionResult:
        try:
            suggestion = self._repo.add(row)
            self._log_submitted(suggestion, submitter)
            return SubmissionResult(suggestion, replayed=False)
        except IntegrityError:
            self._repo.rollback()
            existing = submitter.find_replay(self._repo, idempotency_key)
            if existing is None:
                raise
            return SubmissionResult(existing, replayed=True)

    def _log_submitted(self, suggestion: Suggestion, submitter: Submitter) -> None:
        actor = submitter.event_actor()
        self._events.record(
            suggestion.id, EventType.SUBMITTED, actor_user_id=actor.user_id, actor_api_key_id=actor.api_key_id
        )

    def _resolve_jurisdiction(self, request: SuggestionCreate) -> UUID:
        jurisdiction_id = self._documents.resolve_jurisdiction_id(
            jurisdiction_id=request.jurisdiction_id, municipality_code=request.municipality_code
        )
        if jurisdiction_id is None:
            raise UnknownJurisdictionError("jurisdiction_id or municipality_code does not resolve to a jurisdiction")
        return jurisdiction_id

    def _check_duplicates(self, handler: Dispatch, jurisdiction_id: UUID, request: SuggestionCreate) -> None:
        conflicts = handler.conflicts(request.payload, jurisdiction_id=jurisdiction_id)
        if conflicts:
            raise DuplicateSuggestionError(conflicts)

    def _build_row(
        self,
        submitter: Submitter,
        request: SuggestionCreate,
        jurisdiction_id: UUID,
        idempotency_key: str | None,
        handler: Dispatch,
    ) -> Suggestion:
        return Suggestion(
            kind=request.kind,
            status=SuggestionStatus.PENDING,
            source_type=submitter.source_type,
            jurisdiction_id=jurisdiction_id,
            payload=request.payload.model_dump(mode="json"),
            source_url=request.source_url,
            normalized_url=handler.normalized_url(request.payload),
            idempotency_key=submitter.stored_idempotency_key(idempotency_key),
            **submitter.row_fields(),
        )
