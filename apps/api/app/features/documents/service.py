from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from app.features.documents.repository import DocumentRepository
from app.models.document import Document
from app.models.jurisdiction import JurisdictionKind
from app.schema.document.read import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    JurisdictionPathNode,
    RequirementRead,
)


def _pick_i18n(
    values: dict[str, object] | None,
    *,
    locale: str,
    enabled: Iterable[str],
) -> str:
    """Resolve JSONB i18n map: requested → de → en → first enabled key → any value."""
    if not values:
        return ""
    enabled_set = set(enabled)
    for code in (locale, "de", "en"):
        if code in values and str(values[code]).strip():
            return str(values[code])
    for key in sorted(enabled_set):
        if key in values and str(values[key]).strip():
            return str(values[key])
    for _k, v in values.items():
        if v is not None and str(v).strip():
            return str(v)
    return ""


class DocumentService:
    """Domain logic for localized document reads."""

    def __init__(self, repository: DocumentRepository) -> None:
        self._repo = repository

    def list_documents(
        self,
        *,
        locale: str,
        enabled_locales: set[str],
        jurisdiction_id: UUID | None,
        municipality_code: str | None = None,
        offset: int,
        limit: int,
    ) -> DocumentListResponse:
        effective_jurisdiction_id = jurisdiction_id
        if municipality_code is not None:
            effective_jurisdiction_id = self._repo.get_municipality_jurisdiction_id(municipality_code=municipality_code)
            if effective_jurisdiction_id is None:
                return DocumentListResponse(
                    items=[],
                    total=0,
                    offset=offset,
                    limit=limit,
                )

        total = self._repo.count(jurisdiction_id=effective_jurisdiction_id)
        rows = self._repo.list_page(jurisdiction_id=effective_jurisdiction_id, offset=offset, limit=limit)
        items = [self._to_summary(row, locale=locale, enabled_locales=enabled_locales) for row in rows]
        return DocumentListResponse(items=items, total=total, offset=offset, limit=limit)

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
                    notes=_pick_i18n(edge.notes_i18n, locale=locale, enabled=enabled_locales) or None,
                )
            )
        return DocumentDetail(
            id=doc.id,
            slug=doc.slug,
            title=_pick_i18n(doc.title_i18n, locale=locale, enabled=enabled_locales),
            description=_pick_i18n(doc.description_i18n, locale=locale, enabled=enabled_locales),
            official_url=doc.official_url,
            jurisdiction_id=doc.jurisdiction_id,
            jurisdiction_path=jurisdiction_path,
            requirements=reqs,
        )

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
            name=_pick_i18n(j.name_i18n, locale=locale, enabled=enabled),
            kind=kind,
            openplz_type=getattr(j, "openplz_type", None),
        )

    def _to_summary(self, doc: Document, *, locale: str, enabled_locales: set[str]) -> DocumentSummary:
        return DocumentSummary(
            id=doc.id,
            slug=doc.slug,
            title=_pick_i18n(doc.title_i18n, locale=locale, enabled=enabled_locales),
            description=_pick_i18n(doc.description_i18n, locale=locale, enabled=enabled_locales),
        )
