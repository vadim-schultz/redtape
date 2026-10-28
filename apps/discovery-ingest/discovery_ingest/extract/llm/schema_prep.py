"""Adapt the extraction schema to what Workers AI JSON mode accepts.

Probe-dependent (chapter E4, Step 0): the default inlines every ``$ref``, because it is not documented whether
Workers AI follows ``$defs``. If the probe shows it does, replace the body of :func:`prepare_schema` with a copy.
"""

from __future__ import annotations

import copy
from typing import Any

Schema = dict[str, Any]
_REF_PREFIX = "#/$defs/"


def _resolve(node: Any, defs: Schema, seen: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        return [_resolve(item, defs, seen) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _follow(node, defs, seen)
    return {key: _resolve(value, defs, seen) for key, value in node.items()}


def _follow(node: Schema, defs: Schema, seen: tuple[str, ...]) -> Any:
    ref = str(node["$ref"])
    name = ref.removeprefix(_REF_PREFIX)
    if name in seen:
        raise ValueError(f"recursive $ref {ref}")
    target = _resolve(copy.deepcopy(defs[name]), defs, (*seen, name))
    extras = {key: _resolve(value, defs, seen) for key, value in node.items() if key != "$ref"}
    return {**target, **extras}


def prepare_schema(schema: Schema) -> Schema:
    """Return a copy of ``schema`` with every ``$ref`` inlined and ``$defs`` removed; raise on a recursive ref."""
    defs = schema.get("$defs", {})
    body = {key: value for key, value in schema.items() if key != "$defs"}
    return dict(_resolve(body, defs, ()))
