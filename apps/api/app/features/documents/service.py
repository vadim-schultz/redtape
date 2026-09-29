from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.features.documents.repository import DocumentRepository
from app.features.taxonomy.service import TaxonomyService
from app.i18n_resolution import pick_i18n
from app.models.document import Document
from app.models.jurisdiction import JurisdictionKind
from app.models.taxonomy import Domain, LifeSituation
from app.schema.document.read import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    JurisdictionPathNode,
    RequirementRead,
)
from app.schema.suggestion.payload import NewDocumentPayload
from app.schema.taxonomy.read import TermRead
from app.url_normalization import normalize_url


def _conflicting_document_ids(
    rows: Sequence[tuple[UUID, str, str | None]], *, slug: str, normalized_url: str
) -> list[UUID]:
    """Ids of rows whose slug or normalized `official_url` matches; pure, no session needed."""
    return [
        doc_id
        for doc_id, doc_slug, official_url in rows
        if doc_slug == slug or (official_url is not None and normalize_url(official_url) == normalized_url)
    ]


@dataclass(frozen=True)
class DocumentFilters:
    """Optional narrowing of the document list; empty code lists mean no filter on that axis."""

    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    domain_codes: Sequence[str] = ()
    situation_codes: Sequence[str] = ()


class DocumentService:
    """Domain logic for localized document reads."""

    def __init__(self, repository: DocumentRepository, taxonomy: TaxonomyService) -> None:
        self._repo = repository
        self._taxonomy = taxonomy

    def list_documents(
        self,
        *,
        locale: str,
        enabled_locales: set[str],
        filters: DocumentFilters,
        offset: int,
        limit: int,
    ) -> DocumentListResponse:
        jurisdiction_id = self._effective_jurisdiction_id(filters)
        if filters.municipality_code is not None and jurisdiction_id is None:
            return DocumentListResponse(items=[], total=0, offset=offset, limit=limit)

        scope = {
            "jurisdiction_id": jurisdiction_id,
            "domain_ids": self._taxonomy.resolve_domain_ids(filters.domain_codes),
            "situation_ids": self._taxonomy.resolve_situation_ids(filters.situation_codes),
        }
        total = self._repo.count(**scope)
        rows = self._repo.list_page(offset=offset, limit=limit, **scope)
        items = [self._to_summary(row, locale=locale, enabled_locales=enabled_locales) for row in rows]
        return DocumentListResponse(items=items, total=total, offset=offset, limit=limit)

    def create_from_suggestion(self, payload: NewDocumentPayload, jurisdiction_id: UUID, slug: str) -> Document:
        """Build and persist a `Document` from an approved suggestion's payload; `slug` is never recomputed."""
        domain_ids, situation_ids = self._resolve_tags(payload)
        document = self._build_document(payload, jurisdiction_id, slug)
        return self._repo.add(document, domain_ids=domain_ids, situation_ids=situation_ids)

    def _resolve_tags(self, payload: NewDocumentPayload) -> tuple[list[UUID], list[UUID]]:
        return self._taxonomy.resolve_domain_ids(payload.domain_codes), self._taxonomy.resolve_situation_ids(
            payload.situation_codes
        )

    def _build_document(self, payload: NewDocumentPayload, jurisdiction_id: UUID, slug: str) -> Document:
        return Document(
            jurisdiction_id=jurisdiction_id,
            slug=slug,
            title_i18n=payload.title_i18n,
            description_i18n=payload.description_i18n or {},
            official_url=payload.official_url,
        )

    def find_conflicts(self, *, jurisdiction_id: UUID, slug: str, normalized_url: str) -> list[UUID]:
        """Ids of documents in `jurisdiction_id` whose slug or normalized official URL matches."""
        rows = self._repo.list_slugs_and_urls(jurisdiction_id)
        return _conflicting_document_ids(rows, slug=slug, normalized_url=normalized_url)

    def get_document_jurisdiction(self, document_id: UUID) -> UUID | None:
        return self._repo.get_jurisdiction_for_document(document_id)

    def requirement_exists(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> UUID | None:
        """Id of the existing `document_requirement` for this exact triple, if any."""
        return self._repo.find_requirement(
            jurisdiction_id=jurisdiction_id,
            parent_document_id=parent_document_id,
            required_document_id=required_document_id,
        )

    def requires_directly(self, parent_document_id: UUID, required_document_id: UUID) -> bool:
        """Whether `parent_document_id` already directly requires `required_document_id`, in any jurisdiction."""
        return self._repo.requirement_edge_exists(
            parent_document_id=parent_document_id, required_document_id=required_document_id
        )

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

    def resolve_jurisdiction_id(self, *, jurisdiction_id: UUID | None, municipality_code: str | None) -> UUID | None:
        """Resolve a raw id or municipality code; a raw id is also checked for existence."""
        filters = DocumentFilters(jurisdiction_id=jurisdiction_id, municipality_code=municipality_code)
        resolved = self._effective_jurisdiction_id(filters)
        if resolved is None:
            return None
        if municipality_code is None and not self._repo.jurisdiction_exists(resolved):
            return None
        return resolved

    def get_document_detail(
        self,
        *,
        document_id: UUID,
        locale: str,
        enabled_locales: set[str],
    ) -> DocumentDetail | None:
        doc = self._repo.get_by_id(document_id)
        if doc is None:
            return None

        jurisdiction_path = [
            self._jurisdiction_to_path_node(j, locale=locale, enabled=enabled_locales)
            for j in self._repo.get_jurisdiction_path(jurisdiction_id=doc.jurisdiction_id)
        ]

        reqs: list[RequirementRead] = []
        for edge in doc.outgoing_requirements:
            req_doc = edge.required_document
            reqs.append(
                RequirementRead(
                    id=edge.id,
                    required_document=self._to_summary(req_doc, locale=locale, enabled_locales=enabled_locales),
                    notes=pick_i18n(edge.notes_i18n, locale=locale, enabled=enabled_locales) or None,
                )
            )
        return DocumentDetail(
            id=doc.id,
            slug=doc.slug,
            title=pick_i18n(doc.title_i18n, locale=locale, enabled=enabled_locales),
            description=pick_i18n(doc.description_i18n, locale=locale, enabled=enabled_locales),
            official_url=doc.official_url,
            jurisdiction_id=doc.jurisdiction_id,
            jurisdiction_path=jurisdiction_path,
            requirements=reqs,
            domains=self._term_reads(doc.domains, locale, enabled_locales),
            life_situations=self._term_reads(doc.life_situations, locale, enabled_locales),
        )

    def _term_reads(self, terms: Sequence[Domain | LifeSituation], locale: str, enabled: set[str]) -> list[TermRead]:
        return [self._taxonomy.to_term_read(term, locale=locale, enabled_locales=enabled) for term in terms]

    def _jurisdiction_to_path_node(
        self,
        jurisdiction: object,
        *,
        locale: str,
        enabled: set[str],
    ) -> JurisdictionPathNode:
        # Infer whether REGION means "state" or "district" by OpenPLZ roles.
        j = jurisdiction  # type: ignore[assignment]
        kind = "REGION"
        if j.kind == JurisdictionKind.COUNTRY:
            kind = "COUNTRY"
        elif j.kind == JurisdictionKind.MUNICIPALITY:
            kind = "MUNICIPALITY"
        else:
            if getattr(j, "administrative_roles", []) and "DISTRICT" in j.administrative_roles:
                kind = "DISTRICT"

        return JurisdictionPathNode(
            code=str(getattr(j, "code", "") or ""),
            name=pick_i18n(j.name_i18n, locale=locale, enabled=enabled),
            kind=kind,
            openplz_type=getattr(j, "openplz_type", None),
        )

    def _to_summary(self, doc: Document, *, locale: str, enabled_locales: set[str]) -> DocumentSummary:
        return DocumentSummary(
            id=doc.id,
            slug=doc.slug,
            title=pick_i18n(doc.title_i18n, locale=locale, enabled=enabled_locales),
            description=pick_i18n(doc.description_i18n, locale=locale, enabled=enabled_locales),
        )
