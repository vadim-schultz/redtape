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


def _codes(values: list[str] | None) -> tuple[str, ...]:
    """Normalize repeated or comma-separated taxonomy query values."""
    return tuple(dict.fromkeys(code.strip() for value in values or () for code in value.split(",") if code.strip()))


def _combine(*values: list[str] | None) -> list[str]:
    """Combine repeated query aliases before taxonomy code normalization."""
    return [value for group in values if group for value in group]


def provide_document_list_query(
    page: PageParams,
    jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
    municipality_code: str | None = Parameter(query="municipality_code", default=None),
    category: list[str] | None = Parameter(query="category", default=None),
    category_filter: list[str] | None = Parameter(query="filter[category]", default=None),
    domain: list[str] | None = Parameter(query="domain", default=None),
    domain_filter: list[str] | None = Parameter(query="filter[domain]", default=None),
    group: list[str] | None = Parameter(query="group", default=None),
    group_filter: list[str] | None = Parameter(query="filter[group]", default=None),
    situation: list[str] | None = Parameter(query="situation", default=None),
    situation_filter: list[str] | None = Parameter(query="filter[situation]", default=None),
) -> DocumentListQuery:
    """Collect the document list query parameters into one object."""
    filters = DocumentFilters(
        jurisdiction_id=jurisdiction_id,
        municipality_code=municipality_code,
        category_codes=_codes(_combine(category, category_filter)),
        domain_codes=_codes(_combine(domain, domain_filter)),
        group_codes=_codes(_combine(group, group_filter)),
        situation_codes=_codes(_combine(situation, situation_filter)),
    )
    return DocumentListQuery(filters=filters, page=page)
