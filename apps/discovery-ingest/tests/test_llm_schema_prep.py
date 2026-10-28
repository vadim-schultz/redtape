"""prepare_schema: the one place that adapts the E3 schema to what Workers AI accepts (chapter E4, loop A)."""

from __future__ import annotations

import json

import pytest
from discovery_ingest.extract.llm.schema import build_json_schema
from discovery_ingest.extract.llm.schema_prep import prepare_schema

from llm_fakes import taxonomy


def test_refs_are_inlined_and_the_defs_are_dropped() -> None:
    """prepare_schema · the E3 schema keeps its shape but has no $ref or $defs left."""
    original = build_json_schema(taxonomy())

    prepared = prepare_schema(original)

    text = json.dumps(prepared)
    assert "$ref" not in text and "$defs" not in prepared
    assert (
        prepared["properties"]["documents"]["items"]["properties"]["role"]
        == original["$defs"]["DocumentItem"]["properties"]["role"]
    )
    assert "$defs" in original, "the input is not mutated"


def test_a_schema_without_refs_is_returned_equal_and_a_cycle_is_refused() -> None:
    """prepare_schema · plain schemas pass through; a recursive $ref raises instead of looping."""
    plain = {"type": "object", "properties": {"a": {"type": "string"}}}
    cyclic = {"$defs": {"Node": {"properties": {"next": {"$ref": "#/$defs/Node"}}}}, "$ref": "#/$defs/Node"}

    assert prepare_schema(plain) == plain
    with pytest.raises(ValueError, match="recursive"):
        prepare_schema(cyclic)
