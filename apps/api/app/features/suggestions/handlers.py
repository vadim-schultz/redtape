"""Per-kind suggestion behaviour: validation, URL derivation, duplicate lookup, and promotion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Generic, Literal, NamedTuple, Protocol, TypeVar
from uuid import UUID

from app.features.documents.promotion import PromotionPort
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.slugs import pick_title, slugify
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.suggestion import Suggestion, SuggestionKind
from app.schema.suggestion.payload import NewDocumentPayload, NewRequirementPayload
from app.url_normalization import normalize_url

SuggestionPayload = NewDocumentPayload | NewRequirementPayload
PayloadT = TypeVar("PayloadT", bound=NewDocumentPayload | NewRequirementPayload)


class UnknownTaxonomyCodeError(ValueError):
    """Raised when a canonical category code does not exist."""


class UnknownDocumentError(ValueError):
    """Raised when a requirement edge names a document outside the suggestion's jurisdiction."""


class CycleError(ValueError):
    """Raised when a requirement edge would create a direct dependency cycle."""


class PromotionConflictError(ValueError):
    """Raised when a competing suggestion won the race to promote onto the same slug or URL."""


class PayloadKindMismatchError(ValueError):
    """Raised when a payload reaches the handler of a different kind than its own."""


@dataclass(frozen=True)
class Conflict:
    """A catalogue entity that already matches an incoming suggestion (D4)."""

    type: Literal["document", "suggestion", "document_requirement"]
    id: UUID


@dataclass(frozen=True)
class HandlerDeps:
    """What the per-kind handlers read from the rest of the app; each handler takes what it needs."""

    documents: PromotionPort
    taxonomy: TaxonomyService
    suggestions: SuggestionRepository


class KindHandler(Protocol[PayloadT]):
    """Per-kind behaviour for one payload type; `KindDispatch` adapts it to the payload union."""

    @property
    def payload_type(self) -> type[PayloadT]:
        """The payload class this handler accepts."""
        ...

    def validate(self, payload: PayloadT, *, jurisdiction_id: UUID) -> None:
        """Raise when the payload does not fit the jurisdiction or the catalogue."""
        ...

    def normalized_url(self, payload: PayloadT) -> str | None:
        """Return the normalized URL the suggestion is deduplicated on, if it has one."""
        ...

    def conflicts(self, payload: PayloadT, *, jurisdiction_id: UUID) -> list[Conflict]:
        """Catalogue entities and pending suggestions this payload would duplicate."""
        ...

    def promote(self, suggestion: Suggestion) -> UUID:
        """Create the catalogue entity for an approved suggestion and return its id."""
        ...


class Dispatch(Protocol):
    """Per-kind behaviour over the whole payload union, as `SuggestionService` sees it."""

    def validate(self, payload: SuggestionPayload, *, jurisdiction_id: UUID) -> None:
        """Raise when the payload does not fit the jurisdiction or the catalogue."""
        ...

    def normalized_url(self, payload: SuggestionPayload) -> str | None:
        """Return the normalized URL the suggestion is deduplicated on, if it has one."""
        ...

    def conflicts(self, payload: SuggestionPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        """Catalogue entities and pending suggestions this payload would duplicate."""
        ...

    def promote(self, suggestion: Suggestion) -> UUID:
        """Create the catalogue entity for an approved suggestion and return its id."""
        ...


class KindDispatch(Generic[PayloadT]):
    """The one place the payload union is narrowed: check the kind once, then forward to the handler."""

    def __init__(self, handler: KindHandler[PayloadT]) -> None:
        """Wrap one typed handler; the dispatch narrows incoming payloads to its payload type."""
        self._handler = handler

    def validate(self, payload: SuggestionPayload, *, jurisdiction_id: UUID) -> None:
        """Narrow the payload and validate it."""
        self._handler.validate(self._narrow(payload), jurisdiction_id=jurisdiction_id)

    def normalized_url(self, payload: SuggestionPayload) -> str | None:
        """Narrow the payload and derive its normalized URL."""
        return self._handler.normalized_url(self._narrow(payload))

    def conflicts(self, payload: SuggestionPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        """Narrow the payload and look up its duplicates."""
        return self._handler.conflicts(self._narrow(payload), jurisdiction_id=jurisdiction_id)

    def promote(self, suggestion: Suggestion) -> UUID:
        """Promote the stored suggestion; its payload is re-read by the handler."""
        return self._handler.promote(suggestion)

    def _narrow(self, payload: SuggestionPayload) -> PayloadT:
        if not isinstance(payload, self._handler.payload_type):
            raise PayloadKindMismatchError(f"payload {type(payload).__name__} does not match this kind")
        return payload


class DocumentIdentity(NamedTuple):
    """What makes a `new_document` payload a duplicate: its promotion slug and, if it has one, its URL."""

    slug: str
    normalized_url: str | None


def _document_identity(payload: NewDocumentPayload) -> DocumentIdentity:
    url = None if payload.official_url is None else normalize_url(payload.official_url)
    return DocumentIdentity(slugify(pick_title(payload.title_i18n)), url)


class NewDocumentHandler:
    """Behaviour for `new_document` suggestions (chapters 3-4)."""

    payload_type: ClassVar[type[NewDocumentPayload]] = NewDocumentPayload

    def __init__(self, deps: HandlerDeps) -> None:
        """Bind the document port, taxonomy service and suggestion repository from the shared deps."""
        self._documents = deps.documents
        self._taxonomy = deps.taxonomy
        self._suggestions = deps.suggestions

    def validate(self, payload: NewDocumentPayload, *, jurisdiction_id: UUID) -> None:
        """Check that every canonical category code exists; the jurisdiction is not used here."""
        try:
            self._taxonomy.require_category_codes(payload.category_codes)
        except TaxonomyCodeError as exc:
            raise UnknownTaxonomyCodeError(str(exc)) from exc

    def normalized_url(self, payload: NewDocumentPayload) -> str | None:
        """Return the normalized official URL, if the payload has one."""
        return _document_identity(payload).normalized_url

    def conflicts(self, payload: NewDocumentPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        """Documents sharing the slug or URL, and pending suggestions sharing the URL."""
        identity = _document_identity(payload)
        document_ids = self._conflicting_documents(identity, jurisdiction_id)
        pending_ids = self._pending_with_url(jurisdiction_id, identity.normalized_url)
        return [Conflict("document", i) for i in document_ids] + [Conflict("suggestion", i) for i in pending_ids]

    def promote(self, suggestion: Suggestion) -> UUID:
        """Create the document unless its slug or URL was taken since the suggestion was filed."""
        payload = NewDocumentPayload.model_validate(suggestion.payload)
        identity = _document_identity(payload)
        self._check_still_free(identity, jurisdiction_id=suggestion.jurisdiction_id)
        document = self._documents.create_document(payload, suggestion.jurisdiction_id, identity.slug)
        return document.id

    def _check_still_free(self, identity: DocumentIdentity, *, jurisdiction_id: UUID) -> None:
        if self._conflicting_documents(identity, jurisdiction_id):
            raise PromotionConflictError(f"slug {identity.slug!r} was already taken in jurisdiction {jurisdiction_id}")

    def _conflicting_documents(self, identity: DocumentIdentity, jurisdiction_id: UUID) -> list[UUID]:
        return self._documents.find_conflicts(
            jurisdiction_id=jurisdiction_id, slug=identity.slug, normalized_url=identity.normalized_url
        )

    def _pending_with_url(self, jurisdiction_id: UUID, normalized_url: str | None) -> list[UUID]:
        if normalized_url is None:
            return []
        return self._suggestions.find_pending_by_url(jurisdiction_id=jurisdiction_id, normalized_url=normalized_url)


class NewRequirementHandler:
    """Behaviour for `new_requirement` suggestions (chapter 8)."""

    payload_type: ClassVar[type[NewRequirementPayload]] = NewRequirementPayload

    def __init__(self, deps: HandlerDeps) -> None:
        """Bind the document port and suggestion repository; requirement edges need no taxonomy."""
        self._documents = deps.documents
        self._suggestions = deps.suggestions

    def validate(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> None:
        """Check both documents are in the jurisdiction and the edge does not close a cycle."""
        self._check_in_scope(payload.parent_document_id, jurisdiction_id)
        self._check_in_scope(payload.required_document_id, jurisdiction_id)
        if self._documents.requires_directly(payload.required_document_id, payload.parent_document_id):
            raise CycleError("the required document already requires the parent document")

    def _check_in_scope(self, document_id: UUID, jurisdiction_id: UUID) -> None:
        if not self._in_scope(document_id, jurisdiction_id):
            raise UnknownDocumentError(f"document {document_id} is not in this jurisdiction")

    def _in_scope(self, document_id: UUID, jurisdiction_id: UUID) -> bool:
        return self._documents.jurisdiction_of_document(document_id) == jurisdiction_id

    def normalized_url(self, payload: NewRequirementPayload) -> str | None:
        """Return None: requirement edges have no URL to deduplicate on."""
        return None

    def conflicts(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> list[Conflict]:
        """List the existing requirement for this edge and the pending suggestions proposing it."""
        conflicts: list[Conflict] = []
        existing = self._documents.existing_requirement(
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

    def promote(self, suggestion: Suggestion) -> UUID:
        """Create the requirement unless the edge became invalid since the suggestion was filed."""
        payload = NewRequirementPayload.model_validate(suggestion.payload)
        self._check_still_valid(payload, jurisdiction_id=suggestion.jurisdiction_id)
        requirement = self._documents.create_requirement(
            payload.parent_document_id, payload.required_document_id, suggestion.jurisdiction_id, payload.notes_i18n
        )
        return requirement.id

    def _check_still_valid(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> None:
        self._check_still_in_scope(payload.parent_document_id, jurisdiction_id)
        self._check_still_in_scope(payload.required_document_id, jurisdiction_id)
        self._check_no_new_cycle(payload)
        self._check_no_duplicate_edge(payload, jurisdiction_id=jurisdiction_id)

    def _check_still_in_scope(self, document_id: UUID, jurisdiction_id: UUID) -> None:
        if not self._in_scope(document_id, jurisdiction_id):
            raise PromotionConflictError(f"document {document_id} is no longer in jurisdiction {jurisdiction_id}")

    def _check_no_new_cycle(self, payload: NewRequirementPayload) -> None:
        if self._documents.requires_directly(payload.required_document_id, payload.parent_document_id):
            raise PromotionConflictError("promoting this edge would create a direct cycle")

    def _check_no_duplicate_edge(self, payload: NewRequirementPayload, *, jurisdiction_id: UUID) -> None:
        existing = self._documents.existing_requirement(
            jurisdiction_id=jurisdiction_id,
            parent_document_id=payload.parent_document_id,
            required_document_id=payload.required_document_id,
        )
        if existing is not None:
            raise PromotionConflictError(f"requirement edge {existing} already exists")


KIND_HANDLERS: dict[SuggestionKind, type[NewDocumentHandler] | type[NewRequirementHandler]] = {
    SuggestionKind.NEW_DOCUMENT: NewDocumentHandler,
    SuggestionKind.NEW_REQUIREMENT: NewRequirementHandler,
}


def build_dispatch(deps: HandlerDeps) -> dict[SuggestionKind, Dispatch]:
    """One dispatch per kind. Wired by hand: each kind keeps its own payload type, which a loop over `KIND_HANDLERS` would erase."""
    return {
        SuggestionKind.NEW_DOCUMENT: KindDispatch(NewDocumentHandler(deps)),
        SuggestionKind.NEW_REQUIREMENT: KindDispatch(NewRequirementHandler(deps)),
    }
