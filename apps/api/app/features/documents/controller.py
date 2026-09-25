from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, get
from litestar.exceptions import HTTPException, NotFoundException
from litestar.params import Parameter

from app.features.documents.service import DocumentFilters, DocumentService
from app.features.taxonomy.service import TaxonomyCodeError
from app.schema.document.read import DocumentDetail, DocumentListResponse


def _request_locale(request: Request) -> str:
    state = request.scope.get("state") or {}
    return str(state.get("locale", "de"))


class DocumentsController(Controller):
    """Read-only document catalog (Wave 1)."""

    path = "/"

    @get("/", sync_to_thread=True)
    def list_documents(
        self,
        request: Request,
        document_service: DocumentService,
        jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
        municipality_code: str | None = Parameter(query="municipality_code", default=None),
        domain: list[str] | None = Parameter(query="domain", default=None),
        situation: list[str] | None = Parameter(query="situation", default=None),
        offset: int = Parameter(query="offset", default=0, ge=0),
        limit: int = Parameter(query="limit", default=20, ge=1, le=100),
    ) -> DocumentListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        filters = DocumentFilters(
            jurisdiction_id=jurisdiction_id,
            municipality_code=municipality_code,
            domain_codes=domain or (),
            situation_codes=situation or (),
        )
        try:
            return document_service.list_documents(
                locale=locale, enabled_locales=enabled, filters=filters, offset=offset, limit=limit
            )
        except TaxonomyCodeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @get("/{document_id:uuid}", sync_to_thread=True)
    def get_document(
        self,
        request: Request,
        document_service: DocumentService,
        document_id: UUID,
    ) -> DocumentDetail:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        detail = document_service.get_document_detail(document_id=document_id, locale=locale, enabled_locales=enabled)
        if detail is None:
            raise NotFoundException("Document not found")
        return detail
