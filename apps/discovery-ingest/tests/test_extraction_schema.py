"""The extraction model and the JSON schema sent to the model."""

from __future__ import annotations

from typing import Any

import pytest
from discovery_ingest.extract.llm.schema import PageExtraction, build_json_schema
from llm_fakes import taxonomy
from pydantic import ValidationError

DOCUMENT = {"name": "Personalausweis", "role": "required", "quote": "Bitte bringen Sie Ihren Personalausweis mit."}
BASE: dict[str, Any] = {
    "page_kind": "service",
    "domain_codes": ["housing"],
    "situation_codes": [],
    "documents": [DOCUMENT],
    "dependencies": [],
}


def _with(**changes: Any) -> dict[str, Any]:
    return {**BASE, **changes}


def _document(**changes: Any) -> dict[str, Any]:
    return {**DOCUMENT, **changes}


def test_a_valid_extraction_parses_with_defaults() -> None:
    parsed = PageExtraction.model_validate(BASE)
    assert parsed.documents[0].is_optional is False
    assert parsed.documents[0].url is None
    assert parsed.documents[0].condition is None


def test_extra_fields_are_rejected_at_every_level() -> None:
    for payload in (
        _with(surprise=1),
        _with(documents=[_document(surprise=1)]),
        _with(dependencies=[{"parent": "a", "requires": "b", "quote": "q", "surprise": 1}]),
    ):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PageExtraction.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        _with(documents=[DOCUMENT] * 41),
        _with(dependencies=[{"parent": "a", "requires": "b", "quote": "q"}] * 41),
        _with(documents=[_document(name="x" * 121)]),
        _with(documents=[_document(quote="x" * 301)]),
        _with(documents=[_document(quote="")]),
        _with(documents=[_document(name="   ")]),
        _with(documents=[_document(condition="x" * 301)]),
        _with(documents=[_document(role="optional")]),
        _with(page_kind="article"),
        _with(domain_codes=["housing", "housing", "housing"]),
        _with(situation_codes=["a", "b", "c", "d"]),
        {key: value for key, value in BASE.items() if key != "documents"},
    ],
    ids=[
        "documents",
        "dependencies",
        "long-name",
        "long-quote",
        "empty-quote",
        "blank-name",
        "long-condition",
        "bad-role",
        "bad-page-kind",
        "domain-count",
        "situation-count",
        "missing-field",
    ],
)
def test_out_of_range_extractions_are_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PageExtraction.model_validate(payload)


def test_the_json_schema_lists_the_taxonomy_codes_as_enums() -> None:
    schema = build_json_schema(taxonomy())
    properties = schema["properties"]
    assert properties["domain_codes"]["items"]["enum"] == ["housing", "identity-civil-status"]
    assert properties["situation_codes"]["items"]["enum"] == ["moving-house", "birth-of-child"]
    assert properties["domain_codes"]["maxItems"] == 2
    assert properties["situation_codes"]["maxItems"] == 3


def test_the_json_schema_requires_every_top_level_field_and_forbids_extras() -> None:
    schema = build_json_schema(taxonomy())
    assert sorted(schema["required"]) == sorted(PageExtraction.model_fields)
    assert schema["additionalProperties"] is False


def test_an_empty_vocabulary_allows_no_codes_instead_of_an_empty_enum() -> None:
    schema = build_json_schema(taxonomy().model_copy(update={"domains": ()}))
    domains = schema["properties"]["domain_codes"]
    assert "enum" not in domains["items"]
    assert domains["maxItems"] == 0


def test_strings_are_stripped() -> None:
    parsed = PageExtraction.model_validate(_with(documents=[_document(name="  Personalausweis \n", url=" ")]))
    assert parsed.documents[0].name == "Personalausweis"
    assert parsed.documents[0].url is None


@pytest.mark.parametrize("bad", ["Pass\x00port", "Pass\x07port", "Pass\tport", "Pass\nport", "Pass\x7fport"])
def test_control_characters_are_rejected(bad: str) -> None:
    with pytest.raises(ValidationError, match="control character"):
        PageExtraction.model_validate(_with(documents=[_document(name=bad)]))
