"""Read-only HTTP endpoints for the matrix axes and the matrix counts."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.params import Parameter

from app.features.documents.service import DocumentFilters, DocumentService
from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import LifeSituationGroupedRead, MatrixResponse, TermRead
from app.shared.locale import ResolvedLocale


class TaxonomyController(Controller):
    """Read-only matrix axes: domains, life situations and their groups."""

    path = "/"

    @get("/domains", sync_to_thread=True)
    def list_domains(self, taxonomy_service: TaxonomyService, locale: ResolvedLocale) -> list[TermRead]:
        """List the domain terms in the requested locale."""
        return taxonomy_service.list_domains(locale=locale)

    @get("/life-situations", sync_to_thread=True)
    def list_life_situations(
        self, taxonomy_service: TaxonomyService, locale: ResolvedLocale
    ) -> list[LifeSituationGroupedRead]:
        """List the life situations with their group code, in the requested locale."""
        return taxonomy_service.list_situations_with_group(locale=locale)

    @get("/life-situation-groups", sync_to_thread=True)
    def list_life_situation_groups(self, taxonomy_service: TaxonomyService, locale: ResolvedLocale) -> list[TermRead]:
        """List the life-situation group terms in the requested locale."""
        return taxonomy_service.list_situation_groups(locale=locale)

    @get("/matrix", sync_to_thread=True)
    def get_matrix(
        self,
        taxonomy_service: TaxonomyService,
        document_service: DocumentService,
        jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
        municipality_code: str | None = Parameter(query="municipality_code", default=None),
    ) -> MatrixResponse:
        """Return the matrix counts over the documents in scope for the optional jurisdiction or municipality filter."""
        filters = DocumentFilters(jurisdiction_id=jurisdiction_id, municipality_code=municipality_code)
        return taxonomy_service.get_matrix(document_service.document_ids_in_scope(filters))
