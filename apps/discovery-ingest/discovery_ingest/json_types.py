"""Open JSON types: a JSON object, and a JSON Schema document, both built on ``pydantic.JsonValue``."""

from __future__ import annotations

from pydantic import JsonValue

JsonObject = dict[str, JsonValue]
"""A JSON object whose values are any JSON value."""

JsonSchema = JsonObject
"""A JSON Schema document; open JSON that the schema helpers narrow node by node."""

__all__ = ["JsonObject", "JsonSchema", "JsonValue"]
