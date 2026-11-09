"""Cutover vocabulary for retired legacy taxonomy inputs: one place names them and one place builds the rejection.

The legacy domain, life-situation group and life-situation axes were replaced by canonical categories in
Chapter 9. Every request that still names them fails with an explicit 422 instead of being silently widened
or ignored. Only this module decides which names are retired and what the client reads back.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

RETIRED_TAXONOMY_AXES: frozenset[str] = frozenset({"domain", "group", "situation"})
RETIRED_TAXONOMY_FIELDS: frozenset[str] = frozenset(
    {
        "domain_codes",
        "situation_codes",
        "situation_leaf_codes",
        "direct_domain_confidence",
        "direct_situation_confidence",
    }
)
REPLACEMENT_HINT = "use canonical category codes from GET /api/v1/categories instead"

_FILTER_KEY = re.compile(r"^filter\[(?P<axis>[^\[\]]+)\]$")


def retired_taxonomy_message(names: Iterable[str]) -> str:
    """Return the client-facing diagnostic that names every retired input and its replacement."""
    return f"Retired taxonomy input(s): {', '.join(sorted(names))}; {REPLACEMENT_HINT}."


def retired_axis_keys(keys: Iterable[str]) -> list[str]:
    """Return the query keys that name a retired axis, bare (``domain``) or as ``filter[domain]``."""
    return [key for key in keys if _axis_of(key) in RETIRED_TAXONOMY_AXES]


def _axis_of(key: str) -> str:
    match = _FILTER_KEY.match(key)
    return match["axis"] if match else key
