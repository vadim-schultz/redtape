"""Domain logic for creating and reading suggestions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.documents.service import DocumentService
from app.features.events.service import EventLogService
from app.features.suggestions.handlers import (
    KIND_HANDLERS,
    Conflict,
    CycleError,
    KindHandler,
    PromotionConflictError,
    UnknownDocumentError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.transitions import AlreadyDecidedError, SuggestionNotFoundError, SuggestionTransitions
from app.features.taxonomy.service import TaxonomyService
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload
from app.schema.suggestion.read import SuggestionListResponse, SuggestionRead

__all__ = [
    "AlreadyDecidedError",
    "Conflict",
    "CycleError",
    "DuplicateSuggestionError",
    "MissingSourceUrlError",
    "PromotionConflictError",
    "SubmissionResult",
    "SubmitterRef",
    "SuggestionFilters",
    "SuggestionNotFoundError",
    "SuggestionService",
    "UnknownDocumentError",
    "UnknownJurisdictionError",
    "UnknownTaxonomyCodeError",
]

_SUBMITTER_COLUMN = {"user": "submitted_by_user_id", "crawler": "submitted_by_api_key_id"}
_SUBMITTER_SOURCE = {"user": SuggestionSource.HUMAN, "crawler": SuggestionSource.CRAWLER}


class UnknownJurisdictionError(ValueError):
    """Raised when neither the jurisdiction id nor the municipality code resolves."""


class MissingSourceUrlError(ValueError):
    """Raised when a crawler-submitted suggestion has no source_url (D9)."""


@dataclass(frozen=True)
class SubmitterRef:
    """The authenticated principal submitting a suggestion, as a plain value."""

    kind: Literal["user", "crawler"]
    id: UUID


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


@dataclass(frozen=True)
class SuggestionFilters:
    """Optional narrowing of the suggestion list; an empty `status` means no filter on that axis."""

    status: Sequence[SuggestionStatus] = ()
    kind: SuggestionKind | None = None
    source_type: SuggestionSource | None = None
    jurisdiction_id: UUID | None = None


class _FilterKwargs(TypedDict):
    status: Sequence[SuggestionStatus]
    kind: SuggestionKind | None
    source_type: SuggestionSource | None
    jurisdiction_id: UUID | None


def _filter_kwargs(filters: SuggestionFilters) -> _FilterKwargs:
    return {
        "status": filters.status,
        "kind": filters.kind,
        "source_type": filters.source_type,
        "jurisdiction_id": filters.jurisdiction_id,
    }


class SuggestionService:
    """Domain logic for creating a suggestion; dispatches per-kind rules to `KIND_HANDLERS`."""

    def __init__(
        self,
        repository: SuggestionRepository,
        documents: DocumentService,
        taxonomy: TaxonomyService,
        events: EventLogService,
    ) -> None:
        self._repo = repository
        self._documents = documents
        self._events = events
        self._handlers: dict[SuggestionKind, KindHandler] = {
            kind: cls(documents, taxonomy, repository) for kind, cls in KIND_HANDLERS.items()
        }
        self._transitions = SuggestionTransitions(repository, self._handlers, events)

    def create(
        self, *, submitter: SubmitterRef, request: SuggestionCreate, idempotency_key: str | None = None
    ) -> SubmissionResult:
        if (existing := self._replay(submitter, idempotency_key)) is not None:
            return SubmissionResult(existing, replayed=True)
        handler = self._handlers[request.kind]
        jurisdiction_id = self._resolve_jurisdiction(request)
        handler.validate(request.payload, jurisdiction_id=jurisdiction_id)
        self._validate_source_url(submitter, request)
        self._check_duplicates(handler, jurisdiction_id, request.payload)
        row = self._build_row(submitter, request, jurisdiction_id, idempotency_key, handler)
        return self._insert(row, submitter, idempotency_key)

    def preview_conflicts(self, request: SuggestionCreate) -> list[Conflict]:
        """Validate ``request`` and return what creating it would duplicate; never writes."""
        handler = self._handlers[request.kind]
        jurisdiction_id = self._resolve_jurisdiction(request)
        handler.validate(request.payload, jurisdiction_id=jurisdiction_id)
        return handler.conflicts(request.payload, jurisdiction_id=jurisdiction_id)

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        return self._repo.get(suggestion_id)

    def list_suggestions(self, *, filters: SuggestionFilters, offset: int, limit: int) -> SuggestionListResponse:
        """Return one page of suggestions matching ``filters``."""
        total = self._repo.count(**_filter_kwargs(filters))
        rows = self._repo.list_page(offset=offset, limit=limit, **_filter_kwargs(filters))
        items = [SuggestionRead.from_row(row, submitter_display_name=name) for row, name in rows]
        return SuggestionListResponse(items=items, total=total, offset=offset, limit=limit)

    def get_suggestion(self, suggestion_id: UUID) -> SuggestionRead | None:
        found = self._repo.get_with_submitter(suggestion_id)
        if found is None:
            return None
        suggestion, name = found
        return SuggestionRead.from_row(suggestion, submitter_display_name=name)

    def transition_to(
        self, suggestion_id: UUID, new_status: SuggestionStatus, actor: AppUser | None, reason: str | None = None
    ) -> Suggestion:
        """Delegate to `SuggestionTransitions`, the one place `status` changes (D5)."""
        return self._transitions.transition_to(suggestion_id, new_status, actor, reason)

    def _replay(self, submitter: SubmitterRef, idempotency_key: str | None) -> Suggestion | None:
        """Keys are only honoured for API keys (D8); a human's header is ignored."""
        if submitter.kind != "crawler" or idempotency_key is None:
            return None
        return self._repo.get_by_idempotency_key(api_key_id=submitter.id, idempotency_key=idempotency_key)

    def _validate_source_url(self, submitter: SubmitterRef, request: SuggestionCreate) -> None:
        if submitter.kind == "crawler" and request.source_url is None:
            raise MissingSourceUrlError("source_url is required for crawler submissions")

    def _insert(self, row: Suggestion, submitter: SubmitterRef, idempotency_key: str | None) -> SubmissionResult:
        try:
            suggestion = self._repo.add(row)
            self._log_submitted(suggestion, submitter)
            return SubmissionResult(suggestion, replayed=False)
        except IntegrityError:
            self._repo.rollback()
            existing = self._replay(submitter, idempotency_key)
            if existing is None:
                raise
            return SubmissionResult(existing, replayed=True)

    def _log_submitted(self, suggestion: Suggestion, submitter: SubmitterRef) -> None:
        actor_user_id = submitter.id if submitter.kind == "user" else None
        actor_api_key_id = submitter.id if submitter.kind == "crawler" else None
        self._events.record(
            suggestion.id, EventType.SUBMITTED, actor_user_id=actor_user_id, actor_api_key_id=actor_api_key_id
        )

    def _resolve_jurisdiction(self, request: SuggestionCreate) -> UUID:
        jurisdiction_id = self._documents.resolve_jurisdiction_id(
            jurisdiction_id=request.jurisdiction_id, municipality_code=request.municipality_code
        )
        if jurisdiction_id is None:
            raise UnknownJurisdictionError("jurisdiction_id or municipality_code does not resolve to a jurisdiction")
        return jurisdiction_id

    def _check_duplicates(
        self, handler: KindHandler, jurisdiction_id: UUID, payload: NewDocumentPayload | NewRequirementPayload
    ) -> None:
        conflicts = handler.conflicts(payload, jurisdiction_id=jurisdiction_id)
        if conflicts:
            raise DuplicateSuggestionError(conflicts)

    def _build_row(
        self,
        submitter: SubmitterRef,
        request: SuggestionCreate,
        jurisdiction_id: UUID,
        idempotency_key: str | None,
        handler: KindHandler,
    ) -> Suggestion:
        return Suggestion(
            kind=request.kind,
            status=SuggestionStatus.PENDING,
            source_type=_SUBMITTER_SOURCE[submitter.kind],
            jurisdiction_id=jurisdiction_id,
            payload=request.payload.model_dump(mode="json"),
            source_url=request.source_url,
            normalized_url=handler.normalized_url(request.payload),
            idempotency_key=idempotency_key if submitter.kind == "crawler" else None,
            **{_SUBMITTER_COLUMN[submitter.kind]: submitter.id},
        )
