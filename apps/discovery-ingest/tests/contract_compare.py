"""Directional comparison of an ingest wire model's JSON Schema with the API model it mirrors.

Two directions cover the two ways a pair talks. ``request``: ingest sends, the API validates, so ingest must
never send what the API rejects. ``response``: the API sends, ingest validates, so ingest must accept every
value the API can send. Only properties, required names, nullability, closed value sets and scalar bounds are
compared; nested models are compared through their own pair.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from discovery_ingest.json_types import JsonObject, JsonValue

Direction = Literal["request", "response"]

BOUND_KEYS = (
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "minimum",
    "maximum",
)
UPPER_BOUND_KEYS = frozenset({"maxLength", "maxItems", "maxProperties", "maximum"})
_MAX_REFERENCE_HOPS = 8


@dataclass(frozen=True, slots=True)
class _FieldShape:
    """What one field admits: whether null is allowed, its closed value set if any, and its scalar bounds."""

    nullable: bool
    enum: tuple[str, ...] | None
    bounds: Mapping[str, float]


def compare(
    ingest: JsonObject,
    api: JsonObject,
    direction: Direction,
    enums: Mapping[str, Sequence[str]] | None = None,
) -> list[str]:
    """Return one readable problem per drift between ``ingest`` and ``api``; an empty list means compatible.

    ``enums`` maps a field name to the value set the API accepts or sends for it, for fields the API types
    as a bare string. Use it when the API's schema cannot express the closed set, and not otherwise.
    """
    ingest_defs = _defs(ingest)
    api_defs = _defs(api)
    ingest_properties = _properties(ingest)
    api_properties = _properties(api)
    ingest_required = _required(ingest)
    api_required = _required(api)
    overrides = enums or {}

    problems = [
        f"{name}: the ingest field is not in the API model"
        for name in sorted(ingest_properties.keys() - api_properties.keys())
    ]
    if direction == "request":
        problems += [
            f"{name}: the API requires it and ingest does not send it"
            for name in sorted(api_required - ingest_properties.keys())
        ]
    for name in sorted(ingest_properties.keys() & api_properties.keys()):
        sent = _shape(ingest_properties[name], ingest_defs)
        accepted = _shape(api_properties[name], api_defs)
        if name in overrides and accepted.enum is None:
            accepted = replace(accepted, enum=tuple(overrides[name]))
        if direction == "request":
            problems += _request_field_problems(
                name,
                sent=sent,
                accepted=accepted,
                ingest_may_omit=name not in ingest_required and not _has_non_null_default(ingest_properties[name]),
                api_requires=name in api_required,
            )
        else:
            problems += _response_field_problems(
                name,
                sent=sent,
                accepted=accepted,
                ingest_requires=name in ingest_required,
                api_may_omit=name not in api_required,
            )
    return problems


def body_problems(body: JsonValue, schema: JsonObject) -> list[str]:
    """Return why a recorded JSON request ``body`` breaks the API request ``schema``; an empty list means it does not."""
    if not isinstance(body, dict):
        return ["the body is not a JSON object"]
    defs = _defs(schema)
    properties = _properties(schema)
    problems = [f"{key}: the API has no such field" for key in sorted(body.keys() - properties.keys())]
    problems += [f"{key}: the API requires it and the body omits it" for key in sorted(_required(schema) - body.keys())]
    for key, value in body.items():
        if key not in properties:
            continue
        shape = _shape(properties[key], defs)
        if value is None:
            if not shape.nullable:
                problems.append(f"{key}: null where the API rejects null")
            continue
        for item in value if isinstance(value, list) else [value]:
            if shape.enum is not None and isinstance(item, str) and item not in shape.enum:
                problems.append(f"{key}: {item!r} is not a value the API accepts")
    return problems


def _request_field_problems(
    name: str,
    *,
    sent: _FieldShape,
    accepted: _FieldShape,
    ingest_may_omit: bool,
    api_requires: bool,
) -> list[str]:
    """Return the request-direction problems of one field that both sides declare."""
    problems: list[str] = []
    if api_requires and ingest_may_omit:
        problems.append(f"{name}: the API requires it but ingest may omit it")
    if sent.nullable and not accepted.nullable:
        problems.append(f"{name}: ingest may send null where the API rejects null")
    if accepted.enum is not None:
        if sent.enum is None:
            problems.append(f"{name}: the API accepts only {list(accepted.enum)}; ingest sends any string")
        else:
            extra = [value for value in sent.enum if value not in accepted.enum]
            if extra:
                problems.append(f"{name}: ingest sends values the API rejects: {extra}")
    for key, value in sent.bounds.items():
        if key not in accepted.bounds:
            continue
        limit = accepted.bounds[key]
        if key in UPPER_BOUND_KEYS and value > limit:
            problems.append(f"{name}: ingest {key}={value:g} is looser than the API's {limit:g}")
        if key not in UPPER_BOUND_KEYS and value < limit:
            problems.append(f"{name}: ingest {key}={value:g} is looser than the API's {limit:g}")
    for key, limit in accepted.bounds.items():
        if key not in sent.bounds:
            problems.append(f"{name}: the API bounds {key}={limit:g} and ingest does not")
    return problems


def _response_field_problems(
    name: str,
    *,
    sent: _FieldShape,
    accepted: _FieldShape,
    ingest_requires: bool,
    api_may_omit: bool,
) -> list[str]:
    """Return the response-direction problems of one field that both sides declare."""
    problems: list[str] = []
    if ingest_requires and api_may_omit:
        problems.append(f"{name}: ingest requires it but the API may omit it")
    if accepted.nullable and not sent.nullable:
        problems.append(f"{name}: the API may send null and ingest rejects null")
    if accepted.enum is not None and sent.enum is not None:
        missing = [value for value in accepted.enum if value not in sent.enum]
        if missing:
            problems.append(f"{name}: the API may send values ingest rejects: {missing}")
    for key, value in sent.bounds.items():
        if key not in accepted.bounds:
            problems.append(f"{name}: ingest bounds {key}={value:g} and the API does not")
            continue
        limit = accepted.bounds[key]
        if key in UPPER_BOUND_KEYS and limit > value:
            problems.append(f"{name}: the API may send {key}={limit:g}; ingest accepts only {value:g}")
        if key not in UPPER_BOUND_KEYS and limit < value:
            problems.append(f"{name}: the API may send {key}={limit:g}; ingest accepts only {value:g}")
    return problems


def _shape(node: JsonObject, defs: JsonObject) -> _FieldShape:
    """Return the nullability, closed value set and scalar bounds that a field schema admits."""
    branch = _resolve(node, defs)
    bounds = dict(_scalar_bounds(node))
    nullable = False
    options = branch.get("anyOf")
    if isinstance(options, list):
        members = [_resolve(_node(option), defs) for option in options]
        nullable = any(member.get("type") == "null" for member in members)
        present = [member for member in members if member.get("type") != "null"]
        if len(present) != 1:
            return _FieldShape(nullable=nullable, enum=None, bounds=bounds)
        branch = present[0]
    bounds.update(_scalar_bounds(branch))
    return _FieldShape(nullable=nullable, enum=_enum_values(branch, defs), bounds=bounds)


def _enum_values(branch: JsonObject, defs: JsonObject) -> tuple[str, ...] | None:
    """Return the closed value set of a schema, reading an array's items when the array holds an enum.

    A one-value ``Literal`` is rendered as ``const`` rather than ``enum``, so both count as a closed set.
    """
    values = branch.get("enum")
    if isinstance(values, list):
        return tuple(str(value) for value in values)
    if "const" in branch:
        return (str(branch["const"]),)
    if branch.get("type") == "array" and isinstance(branch.get("items"), dict):
        return _enum_values(_resolve(_node(branch.get("items")), defs), defs)
    return None


def _scalar_bounds(node: JsonObject) -> dict[str, float]:
    """Return the numeric bounds a schema node states, keyed by their JSON Schema keyword."""
    bounds: dict[str, float] = {}
    for key in BOUND_KEYS:
        value = node.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            bounds[key] = float(value)
    return bounds


def _resolve(node: JsonObject, defs: JsonObject) -> JsonObject:
    """Follow ``$ref`` links and single-item ``allOf`` wrappers to the schema they name."""
    current = node
    for _ in range(_MAX_REFERENCE_HOPS):
        reference = current.get("$ref")
        if isinstance(reference, str):
            target = defs.get(reference.rsplit("/", 1)[-1])
            if not isinstance(target, dict):
                raise KeyError(f"unresolved schema reference {reference}")
            current = target
            continue
        wrapped = current.get("allOf")
        if isinstance(wrapped, list) and len(wrapped) == 1:
            current = _node(wrapped[0])
            continue
        return current
    raise ValueError("schema references nest deeper than the comparator follows")


def _has_non_null_default(node: JsonObject) -> bool:
    """Return whether an optional field defaults to something other than null (a default factory counts)."""
    return "default" not in node or node["default"] is not None


def _properties(schema: JsonObject) -> dict[str, JsonObject]:
    """Return the property schemas of an object schema, keyed by field name."""
    raw = schema.get("properties")
    if not isinstance(raw, dict):
        return {}
    return {name: _node(value) for name, value in raw.items()}


def _required(schema: JsonObject) -> set[str]:
    """Return the names an object schema requires."""
    raw = schema.get("required")
    if not isinstance(raw, list):
        return set()
    return {item for item in raw if isinstance(item, str)}


def _defs(schema: JsonObject) -> JsonObject:
    """Return the shared ``$defs`` table of a schema document."""
    raw = schema.get("$defs")
    return raw if isinstance(raw, dict) else {}


def _node(value: JsonValue | None) -> JsonObject:
    """Return a schema node, or an empty node when the value is not an object."""
    return value if isinstance(value, dict) else {}
