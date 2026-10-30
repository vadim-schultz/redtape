"""Canonical list query (``sort_by``, ``sort_order``, ``q``, ``filter[field]``) with per-resource allowlists.

A resource declares a ``ListQuerySpec``: the sort keys it can order by and a typed parser per filter field.
``parse_list_query`` turns the raw query string into a validated ``ListQuery`` or raises a
``ValidationException`` that lists every offending parameter. No client text reaches a repository unchecked.
"""

from app.shared.list_query.filters import enum_filter, min_int_filter, text_filter, uuid_filter
from app.shared.list_query.model import FilterParser, FilterValue, ListQuery, ListQuerySpec, SortOrder
from app.shared.list_query.parse import SEARCH_MAX_LENGTH, parse_list_query
from app.shared.list_query.provider import provide_list_query

__all__ = [
    "SEARCH_MAX_LENGTH",
    "FilterParser",
    "FilterValue",
    "ListQuery",
    "ListQuerySpec",
    "SortOrder",
    "enum_filter",
    "min_int_filter",
    "parse_list_query",
    "provide_list_query",
    "text_filter",
    "uuid_filter",
]
