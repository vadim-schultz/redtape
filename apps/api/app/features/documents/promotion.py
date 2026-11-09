"""Writes that promote approved suggestions into documents and requirement edges."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.features.documents.repository import DocumentRepository
from app.models.document import Document, DocumentRequirement
from app.schema.suggestion.payload import NewDocumentPayload

COMMUNITY_SOURCE = "community"


@runtime_checkable
class PromotionPort(Protocol):
    """Everything the suggestion feature asks of documents: promotion writes and the lookups that decide them."""

    def find_conflicts(self, *, jurisdiction_id: UUID, slug: str, normalized_url: str | None) -> list[UUID]:
        """Ids of documents in the jurisdiction that already hold the slug or the normalized URL."""
        ...

    def create_document(
        self,
        payload: NewDocumentPayload,
        jurisdiction_id: UUID,
        slug: str,
    ) -> Document:
        """Persist a document and its canonical category scores."""
        ...

    def create_requirement(
        self, parent_id: UUID, required_id: UUID, jurisdiction_id: UUID, notes_i18n: dict[str, str] | None
    ) -> DocumentRequirement:
        """Persist the requirement edge an approved `new_requirement` suggestion describes."""
        ...

    def jurisdiction_of_document(self, document_id: UUID) -> UUID | None:
        """Return the jurisdiction of a document, or ``None`` when it does not exist."""
        ...

    def existing_requirement(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> UUID | None:
        """Return the id of the requirement edge for this exact triple, if one exists."""
        ...

    def requires_directly(self, parent_document_id: UUID, required_document_id: UUID) -> bool:
        """Whether the parent already directly requires the required document, in any jurisdiction."""
        ...

    def resolve_jurisdiction_id(self, *, jurisdiction_id: UUID | None, municipality_code: str | None) -> UUID | None:
        """Resolve a raw jurisdiction id or a municipality code to an existing jurisdiction id."""
        ...


class DocumentPromotion:
    """Creates documents and requirement edges from approved suggestions; the only document write path."""

    def __init__(self, repository: DocumentRepository) -> None:
        """Bind the promotion writes to the document repository."""
        self._repo = repository

    def find_conflicts(self, *, jurisdiction_id: UUID, slug: str, normalized_url: str | None) -> list[UUID]:
        """Ids of documents in `jurisdiction_id` whose slug or normalized official URL matches (slug only if no URL)."""
        return self._repo.find_conflicting_document_ids(
            jurisdiction_id=jurisdiction_id, slug=slug, normalized_url=normalized_url
        )

    def create_document(
        self,
        payload: NewDocumentPayload,
        jurisdiction_id: UUID,
        slug: str,
    ) -> Document:
        """Build and persist a document; `slug` is never recomputed."""
        document = self._build_document(payload, jurisdiction_id, slug)
        return self._repo.add(
            document,
            category_scores=self._category_scores(payload),
            pvog_leaf_codes=payload.pvog_leaf_codes,
        )

    def create_requirement(
        self, parent_id: UUID, required_id: UUID, jurisdiction_id: UUID, notes_i18n: dict[str, str] | None
    ) -> DocumentRequirement:
        """Build and persist a `DocumentRequirement` from an approved suggestion's payload."""
        requirement = DocumentRequirement(
            parent_document_id=parent_id,
            required_document_id=required_id,
            jurisdiction_id=jurisdiction_id,
            source=COMMUNITY_SOURCE,
            notes_i18n=notes_i18n,
        )
        return self._repo.add_requirement(requirement)

    def jurisdiction_of_document(self, document_id: UUID) -> UUID | None:
        """Return the jurisdiction id of a document, or ``None`` when it does not exist.

        A thin delegation kept on purpose: it is part of `PromotionPort`, so the handlers never touch the repository.
        """
        return self._repo.get_jurisdiction_for_document(document_id)

    def existing_requirement(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> UUID | None:
        """Id of the existing `document_requirement` for this exact triple, if any.

        A thin delegation kept on purpose: it is part of `PromotionPort`, so the handlers never touch the repository.
        """
        return self._repo.find_requirement(
            jurisdiction_id=jurisdiction_id,
            parent_document_id=parent_document_id,
            required_document_id=required_document_id,
        )

    def requires_directly(self, parent_document_id: UUID, required_document_id: UUID) -> bool:
        """Whether `parent_document_id` already directly requires `required_document_id`, in any jurisdiction.

        A thin delegation kept on purpose: it is part of `PromotionPort`, so the handlers never touch the repository.
        """
        return self._repo.requirement_edge_exists(
            parent_document_id=parent_document_id, required_document_id=required_document_id
        )

    def resolve_jurisdiction_id(self, *, jurisdiction_id: UUID | None, municipality_code: str | None) -> UUID | None:
        """Resolve a municipality code, or check that a raw id names an existing jurisdiction."""
        if municipality_code is not None:
            return self._repo.get_municipality_jurisdiction_id(municipality_code=municipality_code)
        if jurisdiction_id is None or not self._repo.jurisdiction_exists(jurisdiction_id):
            return None
        return jurisdiction_id

    @staticmethod
    def _category_scores(payload: NewDocumentPayload) -> dict[str, float]:
        """Return each category's confidence.

        A code missing from `payload.tag_confidence` (including when it is `None`, e.g. a hand-written admin
        creation) is fully confident, the same default the link table uses.
        """
        confidence = payload.tag_confidence or {}
        return {code: confidence.get(code, 1.0) for code in payload.category_codes}

    def _build_document(self, payload: NewDocumentPayload, jurisdiction_id: UUID, slug: str) -> Document:
        return Document(
            jurisdiction_id=jurisdiction_id,
            slug=slug,
            title_i18n=payload.title_i18n,
            description_i18n=payload.description_i18n or {},
            official_url=payload.official_url,
        )
