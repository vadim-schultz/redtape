"""Pure parsing and validation of the canonical list query (``sort_by``, ``q``, ``filter[...]``)."""

from __future__ import annotations

import enum

import pytest
from app.shared.list_query import (
    ListQuerySpec,
    SortOrder,
    enum_filter,
    min_int_filter,
    parse_list_query,
)
from litestar.exceptions import ValidationException


class Colour(enum.StrEnum):
    """Enum filter fixture."""

    RED = "red"
    BLUE = "blue"


SPEC = ListQuerySpec(
    sort_keys=frozenset({"name", "created_at"}),
    filters={"colour": enum_filter(Colour), "min_size": min_int_filter(0)},
)


def _errors(raw: dict[str, str]) -> list[dict[str, str]]:
    with pytest.raises(ValidationException) as raised:
        parse_list_query(raw, SPEC)
    assert isinstance(raised.value.extra, list)
    return [dict(error) for error in raised.value.extra]  # type: ignore[arg-type]


def test_list_query_parses_canonical_sort_search_and_typed_filters() -> None:
    query = parse_list_query(
        {
            "sort_by": "name",
            "sort_order": "desc",
            "q": "pass",
            "filter[colour]": "red",
            "filter[min_size]": "3",
            "offset": "20",
        },
        SPEC,
    )

    assert (query.sort_by, query.sort_order, query.q) == ("name", SortOrder.DESC, "pass")
    assert dict(query.filters) == {"colour": Colour.RED, "min_size": 3}


def test_list_query_defaults_to_no_sort_search_or_filters() -> None:
    query = parse_list_query({"offset": "0", "limit": "20", "status": "legacy"}, SPEC)

    assert (query.sort_by, query.sort_order, query.q, dict(query.filters)) == (None, None, None, {})


def test_list_query_rejects_an_unknown_sort_field() -> None:
    [error] = _errors({"sort_by": "password; drop table"})

    assert (error["key"], error["source"]) == ("sort_by", "query")


def test_list_query_rejects_an_invalid_sort_order_and_a_lone_sort_order() -> None:
    assert [e["key"] for e in _errors({"sort_by": "name", "sort_order": "sideways"})] == ["sort_order"]
    assert [e["key"] for e in _errors({"sort_order": "asc"})] == ["sort_order"]


@pytest.mark.parametrize(
    ("key", "value"),
    [("filter[colour]", "green"), ("filter[min_size]", "-1"), ("filter[min_size]", "many"), ("filter[size]", "1")],
)
def test_list_query_rejects_an_invalid_or_unknown_filter(key: str, value: str) -> None:
    assert [error["key"] for error in _errors({key: value})] == [key]


def test_list_query_rejects_an_empty_or_oversized_search_term() -> None:
    assert [e["key"] for e in _errors({"q": ""})] == ["q"]
    assert [e["key"] for e in _errors({"q": "x" * 201})] == ["q"]


def test_list_query_reports_every_invalid_parameter_at_once() -> None:
    errors = _errors({"sort_by": "nope", "filter[colour]": "green"})

    assert sorted(error["key"] for error in errors) == ["filter[colour]", "sort_by"]
