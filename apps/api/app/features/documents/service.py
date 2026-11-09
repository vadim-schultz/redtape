"""Document read use cases: paged lists, scope resolution and localized details."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.features.documents.document_read import DocumentReadMapper
from app.features.documents.repository import DocumentRepository
from app.features.taxonomy.service import TaxonomyService
from app.schema.document.read import (
    DocumentDetail,
    DocumentListResponse,
)
from app.shared.locale import ResolvedLocale


@dataclass(frozen=True)
class DocumentFilters:
    """Optional jurisdiction scope and canonical category narrowing for the document list."""

    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    category_codes: Sequence[str] = ()


class DocumentService:
    """Read-only document logic for lists, scopes and localized details."""

    def __init__(self, repository: DocumentRepository, taxonomy: TaxonomyService) -> None:
        """Bind the service to its repository and taxonomy lookups."""
        self._repo = repository
        self._taxonomy = taxonomy
        self._reader = DocumentReadMapper(taxonomy)

    def list_documents(
        self,
        *,
        locale: str,
        enabled_locales: set[str],
        filters: DocumentFilters,
        offset: int,
        limit: int,
    ) -> DocumentListResponse:
        """Return one localized page of documents matching ``filters``."""
        jurisdiction_id = self._effective_jurisdiction_id(filters)
        if filters.municipality_code is not None and jurisdiction_id is None:
            return DocumentListResponse(items=[], total=0, offset=offset, limit=limit)

        category_ids = self._taxonomy.resolve_category_ids(self._expanded_codes(filters))
        total = self._repo.count(jurisdiction_id=jurisdiction_id, category_ids=category_ids)
        rows = self._repo.list_page(
            offset=offset, limit=limit, jurisdiction_id=jurisdiction_id, category_ids=category_ids
        )
        locales = ResolvedLocale(code=locale, enabled=enabled_locales)
        items = [self._reader.summary(row, locales) for row in rows]
        return DocumentListResponse(items=items, total=total, offset=offset, limit=limit)

    def _effective_jurisdiction_id(self, filters: DocumentFilters) -> UUID | None:
        if filters.municipality_code is None:
            return filters.jurisdiction_id
        return self._repo.get_municipality_jurisdiction_id(municipality_code=filters.municipality_code)

    def _expanded_codes(self, filters: DocumentFilters) -> tuple[str, ...]:
        """Expand the selected categories to their descendants; an unknown code is a validation error."""
        return self._taxonomy.expand_category_codes(filters.category_codes) if filters.category_codes else ()

    def get_document_detail(
        self,
        *,
        document_id: UUID,
        locale: str,
        enabled_locales: set[str],
    ) -> DocumentDetail | None:
        """Return the localized detail for one document, or ``None`` when it does not exist."""
        doc = self._repo.get_by_id(document_id)
        if doc is None:
            return None
        path = self._repo.get_jurisdiction_path(jurisdiction_id=doc.jurisdiction_id)
        confidence = self._repo.get_category_confidence(document_id)
        return self._reader.detail(doc, path, ResolvedLocale(code=locale, enabled=enabled_locales), confidence)
