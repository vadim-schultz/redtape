"""Query-string DTO for the document list endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Request
from litestar.exceptions import HTTPException
from litestar.params import Parameter

from app.features.documents.service import DocumentFilters
from app.shared.paging import PageParams
from app.shared.retired_taxonomy import retired_axis_keys, retired_taxonomy_message


@dataclass(frozen=True, slots=True)
class DocumentListQuery:
    """Filters plus paging for `GET /documents`."""

    filters: DocumentFilters
    page: PageParams


def _codes(values: list[str] | None) -> tuple[str, ...]:
    """Normalize repeated or comma-separated taxonomy query values."""
    return tuple(dict.fromkeys(code.strip() for value in values or () for code in value.split(",") if code.strip()))


def _combine(*values: list[str] | None) -> list[str]:
    """Combine repeated query aliases before taxonomy code normalization."""
    return [value for group in values if group for value in group]


def provide_document_list_query(
    request: Request,
    page: PageParams,
    jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
    municipality_code: str | None = Parameter(query="municipality_code", default=None),
    category: list[str] | None = Parameter(query="category", default=None),
    category_filter: list[str] | None = Parameter(query="filter[category]", default=None),
) -> DocumentListQuery:
    """Collect the document list query parameters into one object; retired legacy axes fail with 422."""
    retired = retired_axis_keys(request.query_params.keys())
    if retired:
        raise HTTPException(status_code=422, detail=retired_taxonomy_message(retired))
    filters = DocumentFilters(
        jurisdiction_id=jurisdiction_id,
        municipality_code=municipality_code,
        category_codes=_codes(_combine(category, category_filter)),
    )
    return DocumentListQuery(filters=filters, page=page)
