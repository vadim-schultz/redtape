from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.exceptions import HTTPException, NotFoundException

from app.features.documents.query import DocumentListQuery
from app.features.documents.service import DocumentService
from app.features.taxonomy.service import TaxonomyCodeError
from app.schema.document.read import DocumentDetail, DocumentListResponse
from app.shared.locale import ResolvedLocale


class DocumentsController(Controller):
    """Read-only document catalog (Wave 1)."""

    path = "/"

    @get("/", sync_to_thread=True)
    def list_documents(
        self, document_service: DocumentService, locale: ResolvedLocale, document_query: DocumentListQuery
    ) -> DocumentListResponse:
        try:
            return document_service.list_documents(
                locale=locale.code,
                enabled_locales=locale.enabled,
                filters=document_query.filters,
                offset=document_query.page.offset,
                limit=document_query.page.limit,
            )
        except TaxonomyCodeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @get("/{document_id:uuid}", sync_to_thread=True)
    def get_document(
        self, document_service: DocumentService, locale: ResolvedLocale, document_id: UUID
    ) -> DocumentDetail:
        detail = document_service.get_document_detail(
            document_id=document_id, locale=locale.code, enabled_locales=locale.enabled
        )
        if detail is None:
            raise NotFoundException("Document not found")
        return detail
