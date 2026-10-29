"""Typed value objects of the canonical list query."""

from __future__ import annotations

import enum
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

FilterValue = str | int
FilterParser = Callable[[str], FilterValue]
_Value = TypeVar("_Value")


class SortOrder(enum.StrEnum):
    """Direction of the requested sort."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class ListQuerySpec:
    """What one resource lets a client sort by and filter on."""

    sort_keys: frozenset[str]
    filters: Mapping[str, FilterParser]


@dataclass(frozen=True, slots=True)
class ListQuery:
    """Validated sort, search and filter request of one list call."""

    sort_by: str | None = None
    sort_order: SortOrder | None = None
    q: str | None = None
    filters: Mapping[str, FilterValue] = field(default_factory=dict)

    def filter_value(self, key: str, kind: type[_Value]) -> _Value | None:
        """Return the filter ``key`` when it is set and of type ``kind``."""
        value = self.filters.get(key)
        return value if isinstance(value, kind) else None
