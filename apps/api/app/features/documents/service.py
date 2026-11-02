from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.features.documents.document_read import DocumentReadMapper, Locales
from app.features.documents.repository import DocumentRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.document import Document, DocumentRequirement
from app.schema.document.read import (
    DocumentDetail,
    DocumentListResponse,
)
from app.schema.suggestion.payload import NewDocumentPayload
from app.url_normalization import normalize_url


def _conflicting_document_ids(
    rows: Sequence[tuple[UUID, str, str | None]], *, slug: str, normalized_url: str | None
) -> list[UUID]:
    """Ids of rows whose slug or normalized `official_url` matches; pure, no session needed.

    A ``None`` ``normalized_url`` (a URL-less document) matches on the slug alone.
    """
    return [
        doc_id for doc_id, doc_slug, official_url in rows if doc_slug == slug or _same_url(official_url, normalized_url)
    ]


def _same_url(official_url: str | None, normalized_url: str | None) -> bool:
    return official_url is not None and normalized_url is not None and normalize_url(official_url) == normalized_url


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

        scope = {
            "jurisdiction_id": jurisdiction_id,
            "domain_ids": self._taxonomy.resolve_domain_ids(filters.domain_codes),
            "situation_ids": self._taxonomy.resolve_situation_ids(filters.situation_codes),
        }
        total = self._repo.count(**scope)
        rows = self._repo.list_page(offset=offset, limit=limit, **scope)
        locales = Locales(locale, enabled_locales)
        items = [self._reader.summary(row, locales) for row in rows]
        leaf_codes = self._leaf_codes_in_scope(jurisdiction_id, scope["situation_ids"])
        return DocumentListResponse(
            items=items, total=total, offset=offset, limit=limit, available_leaf_codes=leaf_codes
        )

    def available_leaf_codes(self, filters: DocumentFilters) -> list[str]:
        """Distinct PVOG leaf codes in scope; only meaningful once exactly one situation is selected
        (chapter 4 design) — empty for zero or several, same as an unresolvable municipality."""
        if filters.municipality_code is not None and self._effective_jurisdiction_id(filters) is None:
            return []
        situation_ids = self._taxonomy.resolve_situation_ids(filters.situation_codes)
        return self._leaf_codes_in_scope(self._effective_jurisdiction_id(filters), situation_ids)

    def _leaf_codes_in_scope(self, jurisdiction_id: UUID | None, situation_ids: Sequence[UUID]) -> list[str]:
        if len(situation_ids) != 1:
            return []
        return self._repo.leaf_codes_in_scope(jurisdiction_id=jurisdiction_id, situation_ids=situation_ids)

    def create_from_suggestion(self, payload: NewDocumentPayload, jurisdiction_id: UUID, slug: str) -> Document:
        """Build and persist a `Document` from an approved suggestion's payload; `slug` is never recomputed."""
        domain_scores, situation_scores, situation_leaf_codes = self._resolve_tags(payload)
        document = self._build_document(payload, jurisdiction_id, slug)
        return self._repo.add(
            document,
            domain_scores=domain_scores,
            situation_scores=situation_scores,
            situation_leaf_codes=situation_leaf_codes,
        )

    def _resolve_tags(
        self, payload: NewDocumentPayload
    ) -> tuple[dict[UUID, float], dict[UUID, float], dict[UUID, str]]:
        """Resolve each axis' codes to ids and pair them with their given confidence, defaulting to `1.0`.

        A code missing from `payload.tag_confidence` (including when it's `None` entirely, e.g. a
        hand-written admin creation) is treated as fully confident — the same default the link tables'
        own `server_default` uses for a row written without this service at all.
        """
        confidence = payload.tag_confidence or {}
        domain_ids = self._taxonomy.resolve_domain_ids(payload.domain_codes)
        situation_ids = self._taxonomy.resolve_situation_ids(payload.situation_codes)
        domain_scores = self._scores(payload.domain_codes, domain_ids, confidence)
        situation_scores = self._scores(payload.situation_codes, situation_ids, confidence)
        situation_leaf_codes = self._leaf_codes(payload.situation_codes, situation_ids, payload.situation_leaf_codes)
        return domain_scores, situation_scores, situation_leaf_codes

    def _scores(self, codes: Sequence[str], ids: Sequence[UUID], confidence: dict[str, float]) -> dict[UUID, float]:
        return {term_id: confidence.get(code, 1.0) for code, term_id in zip(codes, ids, strict=True)}

    def _leaf_codes(
        self, codes: Sequence[str], ids: Sequence[UUID], leaf_codes: dict[str, str] | None
    ) -> dict[UUID, str]:
        """Resolve `payload.situation_leaf_codes` (code -> leaf code) to the term id it belongs to.

        A code missing from `leaf_codes` (including when it's `None` entirely) simply has no leaf code —
        unlike `tag_confidence`, there is no default to fall back to; the facet is optional.
        """
        given = leaf_codes or {}
        return {term_id: given[code] for code, term_id in zip(codes, ids, strict=True) if code in given}

    def _build_document(self, payload: NewDocumentPayload, jurisdiction_id: UUID, slug: str) -> Document:
        return Document(
            jurisdiction_id=jurisdiction_id,
            slug=slug,
            title_i18n=payload.title_i18n,
            description_i18n=payload.description_i18n or {},
            official_url=payload.official_url,
        )

    def create_requirement_from_suggestion(
        self,
        parent_id: UUID,
        required_id: UUID,
        jurisdiction_id: UUID,
        notes_i18n: dict[str, str] | None,
    ) -> DocumentRequirement:
        """Build and persist a `DocumentRequirement` from an approved suggestion's payload."""
        requirement = DocumentRequirement(
            parent_document_id=parent_id,
            required_document_id=required_id,
            jurisdiction_id=jurisdiction_id,
            source="community",
            notes_i18n=notes_i18n,
        )
        return self._repo.add_requirement(requirement)

    def find_conflicts(self, *, jurisdiction_id: UUID, slug: str, normalized_url: str | None) -> list[UUID]:
        """Ids of documents in `jurisdiction_id` whose slug or normalized official URL matches (slug only if no URL)."""
        rows = self._repo.list_slugs_and_urls(jurisdiction_id)
        return _conflicting_document_ids(rows, slug=slug, normalized_url=normalized_url)

    def get_document_jurisdiction(self, document_id: UUID) -> UUID | None:
        """Return the jurisdiction id of a document, or ``None`` when it does not exist."""
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
        """Return the localized detail for one document, or ``None`` when it does not exist."""
        doc = self._repo.get_by_id(document_id)
        if doc is None:
            return None
        path = self._repo.get_jurisdiction_path(jurisdiction_id=doc.jurisdiction_id)
        confidence = self._repo.get_tag_confidence(document_id)
        return self._reader.detail(doc, path, Locales(locale, enabled_locales), confidence)
