"""Domain logic for creating and reading suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.features.documents.service import DocumentService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.urls import normalize_url
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload

_SUBMITTER_COLUMN = {"user": "submitted_by_user_id", "crawler": "submitted_by_api_key_id"}
_SUBMITTER_SOURCE = {"user": SuggestionSource.HUMAN, "crawler": SuggestionSource.CRAWLER}


class UnknownJurisdictionError(ValueError):
    """Raised when neither the jurisdiction id nor the municipality code resolves."""


class UnknownTaxonomyCodeError(ValueError):
    """Raised when a domain or situation code does not exist."""


@dataclass(frozen=True)
class SubmitterRef:
    """The authenticated principal submitting a suggestion, as a plain value."""

    kind: Literal["user", "crawler"]
    id: UUID


class SuggestionService:
    """Domain logic for creating a suggestion; talks to its repository and the owning feature services."""

    def __init__(self, repository: SuggestionRepository, documents: DocumentService, taxonomy: TaxonomyService) -> None:
        self._repo = repository
        self._documents = documents
        self._taxonomy = taxonomy

    def create(self, *, submitter: SubmitterRef, request: SuggestionCreate) -> Suggestion:
        jurisdiction_id = self._resolve_jurisdiction(request)
        self._validate_codes(request.payload)
        return self._repo.add(self._build_row(submitter, request, jurisdiction_id))

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        return self._repo.get(suggestion_id)

    def _resolve_jurisdiction(self, request: SuggestionCreate) -> UUID:
        jurisdiction_id = self._documents.resolve_jurisdiction_id(
            jurisdiction_id=request.jurisdiction_id, municipality_code=request.municipality_code
        )
        if jurisdiction_id is None:
            raise UnknownJurisdictionError("jurisdiction_id or municipality_code does not resolve to a jurisdiction")
        return jurisdiction_id

    def _validate_codes(self, payload: NewDocumentPayload) -> None:
        try:
            self._taxonomy.resolve_domain_ids(payload.domain_codes)
            self._taxonomy.resolve_situation_ids(payload.situation_codes)
        except TaxonomyCodeError as exc:
            raise UnknownTaxonomyCodeError(str(exc)) from exc

    def _build_row(self, submitter: SubmitterRef, request: SuggestionCreate, jurisdiction_id: UUID) -> Suggestion:
        return Suggestion(
            kind=SuggestionKind.NEW_DOCUMENT,
            status=SuggestionStatus.PENDING,
            source_type=_SUBMITTER_SOURCE[submitter.kind],
            jurisdiction_id=jurisdiction_id,
            payload=request.payload.model_dump(mode="json"),
            source_url=request.source_url,
            normalized_url=normalize_url(request.payload.official_url),
            **{_SUBMITTER_COLUMN[submitter.kind]: submitter.id},
        )
