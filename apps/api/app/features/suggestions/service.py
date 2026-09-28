"""Domain logic for creating and reading suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.documents.service import DocumentService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.slugs import pick_title, slugify
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload
from app.url_normalization import normalize_url

_SUBMITTER_COLUMN = {"user": "submitted_by_user_id", "crawler": "submitted_by_api_key_id"}
_SUBMITTER_SOURCE = {"user": SuggestionSource.HUMAN, "crawler": SuggestionSource.CRAWLER}


class UnknownJurisdictionError(ValueError):
    """Raised when neither the jurisdiction id nor the municipality code resolves."""


class UnknownTaxonomyCodeError(ValueError):
    """Raised when a domain or situation code does not exist."""


class MissingSourceUrlError(ValueError):
    """Raised when a crawler-submitted suggestion has no source_url (D9)."""


@dataclass(frozen=True)
class SubmitterRef:
    """The authenticated principal submitting a suggestion, as a plain value."""

    kind: Literal["user", "crawler"]
    id: UUID


@dataclass(frozen=True)
class Conflict:
    """A catalogue entity that already matches an incoming suggestion (D4)."""

    type: Literal["document", "suggestion"]
    id: UUID


class DuplicateSuggestionError(ValueError):
    """Raised when a `new_document` suggestion matches existing documents or pending suggestions."""

    def __init__(self, conflicts: list[Conflict]) -> None:
        super().__init__(f"duplicate suggestion: {len(conflicts)} conflict(s)")
        self.conflicts = conflicts


@dataclass(frozen=True)
class SubmissionResult:
    """Outcome of `SuggestionService.create`: the row, and whether it's an idempotent replay (D8)."""

    suggestion: Suggestion
    replayed: bool


class SuggestionService:
    """Domain logic for creating a suggestion; talks to its repository and the owning feature services."""

    def __init__(self, repository: SuggestionRepository, documents: DocumentService, taxonomy: TaxonomyService) -> None:
        self._repo = repository
        self._documents = documents
        self._taxonomy = taxonomy

    def create(
        self, *, submitter: SubmitterRef, request: SuggestionCreate, idempotency_key: str | None = None
    ) -> SubmissionResult:
        if (existing := self._replay(submitter, idempotency_key)) is not None:
            return SubmissionResult(existing, replayed=True)
        jurisdiction_id = self._validate(submitter, request)
        self._check_duplicates(jurisdiction_id=jurisdiction_id, payload=request.payload)
        row = self._build_row(submitter, request, jurisdiction_id, idempotency_key)
        return self._insert(row, submitter, idempotency_key)

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        return self._repo.get(suggestion_id)

    def _replay(self, submitter: SubmitterRef, idempotency_key: str | None) -> Suggestion | None:
        """Keys are only honoured for API keys (D8); a human's header is ignored."""
        if submitter.kind != "crawler" or idempotency_key is None:
            return None
        return self._repo.get_by_idempotency_key(api_key_id=submitter.id, idempotency_key=idempotency_key)

    def _validate(self, submitter: SubmitterRef, request: SuggestionCreate) -> UUID:
        jurisdiction_id = self._resolve_jurisdiction(request)
        self._validate_codes(request.payload)
        self._validate_source_url(submitter, request)
        return jurisdiction_id

    def _validate_source_url(self, submitter: SubmitterRef, request: SuggestionCreate) -> None:
        if submitter.kind == "crawler" and request.source_url is None:
            raise MissingSourceUrlError("source_url is required for crawler submissions")

    def _insert(self, row: Suggestion, submitter: SubmitterRef, idempotency_key: str | None) -> SubmissionResult:
        try:
            return SubmissionResult(self._repo.add(row), replayed=False)
        except IntegrityError:
            self._repo.rollback()
            existing = self._replay(submitter, idempotency_key)
            if existing is None:
                raise
            return SubmissionResult(existing, replayed=True)

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

    def _check_duplicates(self, *, jurisdiction_id: UUID, payload: NewDocumentPayload) -> None:
        slug = slugify(pick_title(payload.title_i18n))
        normalized_url = normalize_url(payload.official_url)
        conflicts = self._document_conflicts(jurisdiction_id, slug, normalized_url) + self._pending_conflicts(
            jurisdiction_id, normalized_url
        )
        if conflicts:
            raise DuplicateSuggestionError(conflicts)

    def _document_conflicts(self, jurisdiction_id: UUID, slug: str, normalized_url: str) -> list[Conflict]:
        ids = self._documents.find_conflicts(jurisdiction_id=jurisdiction_id, slug=slug, normalized_url=normalized_url)
        return [Conflict("document", doc_id) for doc_id in ids]

    def _pending_conflicts(self, jurisdiction_id: UUID, normalized_url: str) -> list[Conflict]:
        ids = self._repo.find_pending_by_url(jurisdiction_id=jurisdiction_id, normalized_url=normalized_url)
        return [Conflict("suggestion", sug_id) for sug_id in ids]

    def _build_row(
        self, submitter: SubmitterRef, request: SuggestionCreate, jurisdiction_id: UUID, idempotency_key: str | None
    ) -> Suggestion:
        return Suggestion(
            kind=SuggestionKind.NEW_DOCUMENT,
            status=SuggestionStatus.PENDING,
            source_type=_SUBMITTER_SOURCE[submitter.kind],
            jurisdiction_id=jurisdiction_id,
            payload=request.payload.model_dump(mode="json"),
            source_url=request.source_url,
            normalized_url=normalize_url(request.payload.official_url),
            idempotency_key=idempotency_key if submitter.kind == "crawler" else None,
            **{_SUBMITTER_COLUMN[submitter.kind]: submitter.id},
        )
