"""Adapt the extraction schema to what Workers AI JSON mode accepts.

Probe-dependent (chapter E4, Step 0): the default inlines every ``$ref``, because it is not documented whether
Workers AI follows ``$defs``. If the probe shows it does, replace the body of :func:`prepare_schema` with a copy.
"""

from __future__ import annotations

from pydantic import JsonValue

from discovery_ingest.json_types import JsonObject, JsonSchema

_REF_PREFIX = "#/$defs/"


def _resolve_value(node: JsonValue, defs: JsonObject, seen: tuple[str, ...]) -> JsonValue:
    """Inline the refs under any JSON value; containers are rebuilt, so the input is never shared with the output."""
    if isinstance(node, list):
        return [_resolve_value(item, defs, seen) for item in node]
    if isinstance(node, dict):
        return _resolve_object(node, defs, seen)
    return node


def _resolve_object(node: JsonObject, defs: JsonObject, seen: tuple[str, ...]) -> JsonObject:
    """Inline the refs under a JSON object; an object that is itself a ref becomes its target."""
    if "$ref" in node:
        return _follow(node, defs, seen)
    return {key: _resolve_value(value, defs, seen) for key, value in node.items()}


def _follow(node: JsonObject, defs: JsonObject, seen: tuple[str, ...]) -> JsonObject:
    """Replace a ``$ref`` node with its definition, keeping any sibling keywords that sit beside the ref."""
    ref = node["$ref"]
    if not isinstance(ref, str):
        raise ValueError(f"malformed $ref {ref!r}")
    name = ref.removeprefix(_REF_PREFIX)
    if name in seen:
        raise ValueError(f"recursive $ref {ref}")
    target = defs[name]
    if not isinstance(target, dict):
        raise ValueError(f"$ref {ref} does not name a schema object")
    extras = {key: _resolve_value(value, defs, seen) for key, value in node.items() if key != "$ref"}
    return {**_resolve_object(target, defs, (*seen, name)), **extras}


def prepare_schema(schema: JsonSchema) -> JsonSchema:
    """Return a copy of ``schema`` with every ``$ref`` inlined and ``$defs`` removed; raise on a recursive ref."""
    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        raise ValueError("$defs is not an object")
    body = {key: value for key, value in schema.items() if key != "$defs"}
    return _resolve_object(body, defs, ())
