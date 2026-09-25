from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, get
from litestar.params import Parameter

from app.features.documents.service import DocumentFilters, DocumentService
from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import MatrixResponse, TermRead


def _locale_context(request: Request) -> tuple[str, set[str]]:
    state = request.scope.get("state") or {}
    enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
    return str(state.get("locale", "de")), enabled


class TaxonomyController(Controller):
    """Read-only matrix axes: domains and life situations."""

    path = "/"

    @get("/domains", sync_to_thread=True)
    def list_domains(self, request: Request, taxonomy_service: TaxonomyService) -> list[TermRead]:
        locale, enabled = _locale_context(request)
        return taxonomy_service.list_domains(locale=locale, enabled_locales=enabled)

    @get("/life-situations", sync_to_thread=True)
    def list_life_situations(self, request: Request, taxonomy_service: TaxonomyService) -> list[TermRead]:
        locale, enabled = _locale_context(request)
        return taxonomy_service.list_situations(locale=locale, enabled_locales=enabled)

    @get("/matrix", sync_to_thread=True)
    def get_matrix(
        self,
        taxonomy_service: TaxonomyService,
        document_service: DocumentService,
        jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
        municipality_code: str | None = Parameter(query="municipality_code", default=None),
    ) -> MatrixResponse:
        filters = DocumentFilters(jurisdiction_id=jurisdiction_id, municipality_code=municipality_code)
        return taxonomy_service.get_matrix(document_service.document_ids_in_scope(filters))
