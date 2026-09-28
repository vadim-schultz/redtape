"""Per-kind suggestion behaviour: validation, URL derivation, and duplicate lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID

from app.features.documents.service import DocumentService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.slugs import pick_title, slugify
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.suggestion import SuggestionKind
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload
from app.url_normalization import normalize_url


class UnknownTaxonomyCodeError(ValueError):
    """Raised when a domain or situation code does not exist."""


class UnknownDocumentError(ValueError):
    """Raised when a requirement edge names a document outside the suggestion's jurisdiction."""


class CycleError(ValueError):
    """Raised when a requirement edge would create a direct dependency cycle."""


@dataclass(frozen=True)
class Conflict:
    """A catalogue entity that already matches an incoming suggestion (D4)."""

    type: Literal["document", "suggestion", "document_requirement"]
    id: UUID


class KindHandler(Protocol):
    """Per-kind behaviour a `SuggestionService` dispatches to."""

    def __init__(
        self, documents: DocumentService, taxonomy: TaxonomyService, suggestions: SuggestionRepository
    ) -> None: ...

    def validate(self, payload: Any, *, jurisdiction_id: UUID) -> None: ...

    def normalized_url(self, payload: Any) -> str | None: ...

    def conflicts(self, payload: Any, *, jurisdiction_id: UUID) -> list[Conflict]: ...


class NewDocumentHandler:
    """Behaviour for `new_document` suggestions (chapters 3-4)."""

    def __init__(
        self, documents: DocumentService, taxonomy: TaxonomyService, suggestions: SuggestionRepository
    ) -> None:
        self._documents = documents
        self._taxonomy = taxonomy
        self._suggestions = suggestions

    def validate(self, payload: NewDocumentPayload, *, jurisdiction_id: UUID) -> None:
        try:
            self._taxonomy.resolve_domain_ids(payload.domain_codes)
            self._taxonomy.resolve_situation_ids(payload.situation_codes)
        except TaxonomyCodeError as exc:
            raise UnknownTaxonomyCodeError(str(exc)) from exc

    def normalized_url(self, payload: NewDocumentPayload) -> str | None:
        return normalize_url(payload.official_url)

    def conflicts(self, payload: NewDocumentPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        slug = slugify(pick_title(payload.title_i18n))
        normalized = normalize_url(payload.official_url)
        document_ids = self._documents.find_conflicts(
            jurisdiction_id=jurisdiction_id, slug=slug, normalized_url=normalized
        )
        pending_ids = self._suggestions.find_pending_by_url(jurisdiction_id=jurisdiction_id, normalized_url=normalized)
        return [Conflict("document", i) for i in document_ids] + [Conflict("suggestion", i) for i in pending_ids]


class NewRequirementHandler:
    """Behaviour for `new_requirement` suggestions (chapter 8)."""

    def __init__(
        self, documents: DocumentService, taxonomy: TaxonomyService, suggestions: SuggestionRepository
    ) -> None:
        self._documents = documents
        self._suggestions = suggestions

    def validate(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> None:
        self._check_in_scope(payload.parent_document_id, jurisdiction_id)
        self._check_in_scope(payload.required_document_id, jurisdiction_id)
        if self._documents.requires_directly(payload.required_document_id, payload.parent_document_id):
            raise CycleError("the required document already requires the parent document")

    def _check_in_scope(self, document_id: UUID, jurisdiction_id: UUID) -> None:
        if self._documents.get_document_jurisdiction(document_id) != jurisdiction_id:
            raise UnknownDocumentError(f"document {document_id} is not in this jurisdiction")

    def normalized_url(self, payload: NewRequirementPayload) -> str | None:
        return None

    def conflicts(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        conflicts: list[Conflict] = []
        existing = self._documents.requirement_exists(
            jurisdiction_id=jurisdiction_id,
            parent_document_id=payload.parent_document_id,
            required_document_id=payload.required_document_id,
        )
        if existing is not None:
            conflicts.append(Conflict("document_requirement", existing))
        pending_ids = self._suggestions.find_pending_edge(
            jurisdiction_id=jurisdiction_id,
            parent_document_id=payload.parent_document_id,
            required_document_id=payload.required_document_id,
        )
        return conflicts + [Conflict("suggestion", i) for i in pending_ids]


KIND_HANDLERS: dict[SuggestionKind, type[KindHandler]] = {
    SuggestionKind.NEW_DOCUMENT: NewDocumentHandler,
    SuggestionKind.NEW_REQUIREMENT: NewRequirementHandler,
}
