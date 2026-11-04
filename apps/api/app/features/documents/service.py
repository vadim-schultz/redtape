"""Document read use cases: paged lists, scope resolution, leaf codes and localized details."""

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
    """Optional narrowing of the document list; empty code lists mean no filter on that axis."""

    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    domain_codes: Sequence[str] = ()
    situation_codes: Sequence[str] = ()


class DocumentService:
    """Read-only domain logic for documents: lists, scopes, leaf codes and localized details."""

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

        domain_ids = self._taxonomy.resolve_domain_ids(filters.domain_codes)
        situation_ids = self._taxonomy.resolve_situation_ids(filters.situation_codes)
        total = self._repo.count(jurisdiction_id=jurisdiction_id, domain_ids=domain_ids, situation_ids=situation_ids)
        rows = self._repo.list_page(
            offset=offset,
            limit=limit,
            jurisdiction_id=jurisdiction_id,
            domain_ids=domain_ids,
            situation_ids=situation_ids,
        )
        locales = ResolvedLocale(code=locale, enabled=enabled_locales)
        items = [self._reader.summary(row, locales) for row in rows]
        leaf_codes = self._leaf_codes_in_scope(jurisdiction_id, situation_ids)
        return DocumentListResponse(
            items=items, total=total, offset=offset, limit=limit, available_leaf_codes=leaf_codes
        )

    def available_leaf_codes(self, filters: DocumentFilters) -> list[str]:
        """Return the distinct PVOG leaf codes in scope, but only when exactly one situation is selected.

        Chapter 4 design: zero or several situations, or an unresolvable municipality, give an empty list.
        """
        if filters.municipality_code is not None and self._effective_jurisdiction_id(filters) is None:
            return []
        situation_ids = self._taxonomy.resolve_situation_ids(filters.situation_codes)
        return self._leaf_codes_in_scope(self._effective_jurisdiction_id(filters), situation_ids)

    def _leaf_codes_in_scope(self, jurisdiction_id: UUID | None, situation_ids: Sequence[UUID]) -> list[str]:
        if len(situation_ids) != 1:
            return []
        return self._repo.leaf_codes_in_scope(jurisdiction_id=jurisdiction_id, situation_ids=situation_ids)

    def document_ids_in_scope(self, filters: DocumentFilters) -> list[UUID]:
        """Ids of documents inside the jurisdiction scope; an unresolvable municipality has none."""
        jurisdiction_id = self._effective_jurisdiction_id(filters)
        if filters.municipality_code is not None and jurisdiction_id is None:
            return []
        return self._repo.ids_in_scope(jurisdiction_id=jurisdiction_id)

    def _effective_jurisdiction_id(self, filters: DocumentFilters) -> UUID | None:
        if filters.municipality_code is None:
            return filters.jurisdiction_id
        return self._repo.get_municipality_jurisdiction_id(municipality_code=filters.municipality_code)

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
        confidence = self._repo.get_tag_confidence(document_id)
        return self._reader.detail(doc, path, ResolvedLocale(code=locale, enabled=enabled_locales), confidence)
