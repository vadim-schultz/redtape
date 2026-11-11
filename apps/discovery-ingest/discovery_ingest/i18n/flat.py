"""Nested locale files as dotted keys and back, written deterministically."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TypeAlias

Nested: TypeAlias = dict[str, "str | Nested"]
"""A locale file: objects nested under their dotted key path, strings at the leaves."""


def flatten(tree: Mapping[str, str | Nested], prefix: str = "") -> dict[str, str]:
    """Return ``tree`` as ``{"a.b": text}``."""
    flat: dict[str, str] = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, str):
            flat[path] = value
        else:
            flat.update(flatten(value, path))
    return flat


def _branch(tree: Nested, parts: list[str], key: str) -> Nested:
    """Return the object under ``parts`` in ``tree``, creating it; raise when a text stands in the way."""
    node = tree
    for part in parts:
        child = node.setdefault(part, {})
        if isinstance(child, str):
            raise ValueError(f"key {key!r} needs {part!r} to be an object, but it holds text")
        node = child
    return node


def unflatten(flat: Mapping[str, str]) -> Nested:
    """Return the nested tree of ``flat``; a key below another key's text raises :class:`ValueError`."""
    tree: Nested = {}
    for key in sorted(flat):
        *parts, leaf = key.split(".")
        _branch(tree, parts, key)[leaf] = flat[key]
    return tree


def dump_json(tree: Nested) -> str:
    """Return ``tree`` as sorted, two-space-indented JSON with readable text and one trailing newline."""
    return json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
