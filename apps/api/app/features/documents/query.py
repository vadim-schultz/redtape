"""Query-string DTO for the document list endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar.params import Parameter

from app.features.documents.service import DocumentFilters
from app.shared.paging import PageParams


@dataclass(frozen=True, slots=True)
class DocumentListQuery:
    """Filters plus paging for `GET /documents`."""

    filters: DocumentFilters
    page: PageParams


def provide_document_list_query(
    page: PageParams,
    jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
    municipality_code: str | None = Parameter(query="municipality_code", default=None),
    domain: list[str] | None = Parameter(query="domain", default=None),
    situation: list[str] | None = Parameter(query="situation", default=None),
) -> DocumentListQuery:
    """Collect the document list query parameters into one object."""
    filters = DocumentFilters(
        jurisdiction_id=jurisdiction_id,
        municipality_code=municipality_code,
        domain_codes=domain or (),
        situation_codes=situation or (),
    )
    return DocumentListQuery(filters=filters, page=page)
