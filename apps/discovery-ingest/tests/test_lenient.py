"""Tables for the shared lenient readers and the Pydantic types built on them."""

from __future__ import annotations

import pytest
from discovery_ingest.lenient import (
    LenientText,
    StrText,
    dict_or_none,
    dicts_only,
    dicts_or_none,
    first_present,
    list_or_empty,
    optional_str,
    text_or_none,
)
from pydantic import BaseModel


class _Probe(BaseModel):
    lenient: LenientText = None
    strict: StrText = None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("  ", None),
        (" x ", "x"),
        (0, "0"),
        (7, "7"),
        (True, "True"),
        ([], "[]"),
        ([1], "[1]"),
    ],
)
def test_optional_str_table(value: object, expected: str | None) -> None:
    """optional_str · strings are stripped, other values are coerced with str(), blanks become None."""
    assert optional_str(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("  ", None),
        (" x ", "x"),
        (0, None),
        (7, None),
        (True, None),
        ([], None),
        ({"a": 1}, None),
    ],
)
def test_text_or_none_table(value: object, expected: str | None) -> None:
    """text_or_none · only non-blank strings survive; every other value is ignored."""
    assert text_or_none(value) == expected


def test_first_present_takes_the_first_non_blank_in_order() -> None:
    """first_present · the first truthy value wins and an all-blank input gives None."""
    assert first_present(None, "", "b", "c") == "b"
    assert first_present(None, None) is None
    assert first_present() is None


def test_list_and_dict_validators_are_tolerant() -> None:
    """list and dict helpers · non-containers give empty results and object entries are kept in order."""
    assert list_or_empty("x") == []
    assert list_or_empty([1, "a"]) == [1, "a"]
    assert dicts_only("x") == []
    assert dicts_only(["junk", {"a": 1}, 3, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert dicts_or_none("x") is None
    assert dicts_or_none(["junk", {"a": 1}]) == [{"a": 1}]
    assert dict_or_none([]) is None
    assert dict_or_none({"a": 1}) == {"a": 1}


def test_lenient_text_coerces_and_strict_text_ignores_non_strings() -> None:
    """LenientText coerces a non-string while StrText ignores it; both strip and turn blank into None."""
    model = _Probe.model_validate({"lenient": 10641, "strict": 10641})

    assert model.lenient == "10641"
    assert model.strict is None
    assert _Probe.model_validate({"lenient": " x ", "strict": " y "}).strict == "y"
