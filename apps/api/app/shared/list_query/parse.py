"""Validate a raw query string against a resource's ``ListQuerySpec``."""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.shared.list_query.errors import InvalidParam, attempt, raise_if_any
from app.shared.list_query.model import FilterValue, ListQuery, ListQuerySpec, SortOrder
from app.shared.retired_taxonomy import retired_taxonomy_message

SEARCH_MAX_LENGTH = 200
_FILTER_PARAM = re.compile(r"^filter\[(?P<field>[^\[\]]+)\]$")


def _sort_by(raw: Mapping[str, str], spec: ListQuerySpec) -> str | None:
    value = raw.get("sort_by")
    if value is not None and value not in spec.sort_keys:
        raise InvalidParam("sort_by", f"Expected one of: {', '.join(sorted(spec.sort_keys))}")
    return value


def _sort_order(raw: Mapping[str, str]) -> SortOrder | None:
    value = raw.get("sort_order")
    if value is None:
        return None
    if "sort_by" not in raw:
        raise InvalidParam("sort_order", "sort_order requires sort_by")
    try:
        return SortOrder(value)
    except ValueError:
        raise InvalidParam("sort_order", "Expected one of: asc, desc") from None


def _search(raw: Mapping[str, str]) -> str | None:
    value = raw.get("q")
    if value is not None and not 1 <= len(value) <= SEARCH_MAX_LENGTH:
        raise InvalidParam("q", f"Expected 1 to {SEARCH_MAX_LENGTH} characters")
    return value


def _filter_value(spec: ListQuerySpec, param: str, field_name: str, raw: str) -> FilterValue:
    if field_name in spec.retired_filters:
        raise InvalidParam(param, retired_taxonomy_message([param]))
    parser = spec.filters.get(field_name)
    if parser is None:
        raise InvalidParam(param, f"Unknown filter; allowed: {', '.join(sorted(spec.filters))}")
    try:
        return parser(raw)
    except ValueError as error:
        raise InvalidParam(param, str(error)) from None


def _filter_params(raw: Mapping[str, str]) -> list[tuple[str, str, str]]:
    matches = ((param, _FILTER_PARAM.match(param), value) for param, value in raw.items())
    return [(param, match["field"], value) for param, match, value in matches if match]


def _filters(errors: list[InvalidParam], raw: Mapping[str, str], spec: ListQuerySpec) -> dict[str, FilterValue]:
    params = _filter_params(raw)
    parsed = {name: attempt(errors, _filter_value, spec, param, name, value) for param, name, value in params}
    return {name: value for name, value in parsed.items() if value is not None}


def _bare_retired_params(raw: Mapping[str, str], spec: ListQuerySpec) -> list[InvalidParam]:
    """Name every bare retired key (``domain=``) so it cannot be ignored into an unfiltered list."""
    return [InvalidParam(key, retired_taxonomy_message([key])) for key in raw if key in spec.retired_filters]


def parse_list_query(raw: Mapping[str, str], spec: ListQuerySpec) -> ListQuery:
    """Validate ``raw`` against ``spec``; raise ``ValidationException`` listing every problem."""
    errors: list[InvalidParam] = _bare_retired_params(raw, spec)
    query = ListQuery(
        sort_by=attempt(errors, _sort_by, raw, spec),
        sort_order=attempt(errors, _sort_order, raw),
        q=attempt(errors, _search, raw),
        filters=_filters(errors, raw, spec),
    )
    raise_if_any(errors)
    return query
