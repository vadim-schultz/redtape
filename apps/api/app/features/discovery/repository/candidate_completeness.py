"""Completeness of every candidate in one query: five flags, their count, and the accepted tag codes (D1, D6)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from functools import reduce
from operator import add
from typing import Self
from uuid import UUID

from sqlalchemy import ColumnElement, Integer, Row, cast, select
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.candidate_completeness_flags import FLAG_NAMES, flags_subquery
from app.features.discovery.repository.candidate_sort import directed
from app.shared.list_query import SortOrder

__all__ = [
    "CandidateCompleteness",
    "completeness_columns",
    "completeness_order",
    "completeness_subquery",
]

CODE_FIELDS = ("accepted_domain_codes", "accepted_situation_codes")


@dataclass(frozen=True)
class CandidateCompleteness:
    """The completeness of one candidate: five flags, how many hold, and the accepted tag codes."""

    candidate_id: UUID
    has_domain: bool
    has_situation: bool
    has_edges: bool
    has_snapshot: bool
    has_screenshot: bool
    completeness: int
    complete: bool
    accepted_domain_codes: tuple[str, ...]
    accepted_situation_codes: tuple[str, ...]

    @classmethod
    def from_row(cls, row: Row) -> Self:
        """Build the value from a row of :func:`completeness_columns`, mapping missing code arrays to ``()``."""
        data = dict(row._mapping)
        data.update({name: tuple(data[name] or ()) for name in CODE_FIELDS})
        return cls(**data)


COLUMN_NAMES = tuple(field.name for field in fields(CandidateCompleteness))


def completeness_subquery() -> Subquery:
    """Return one row per candidate id with the flags, ``completeness``, ``complete`` and the accepted codes."""
    flags = flags_subquery()
    total = reduce(add, (cast(flags.c[name], Integer) for name in FLAG_NAMES))
    return select(*flags.c, total.label("completeness"), (total == len(FLAG_NAMES)).label("complete")).subquery()


def completeness_columns(sub: Subquery) -> tuple[ColumnElement, ...]:
    """Return the labelled columns of ``sub`` in the field order of :class:`CandidateCompleteness`."""
    return tuple(sub.c[name] for name in COLUMN_NAMES)


def completeness_order(
    sub: Subquery, mention_count: ColumnElement[int], direction: SortOrder
) -> Sequence[ColumnElement]:
    """Return the order-by pair ``(completeness, mention_count)`` in ``direction``."""
    pair = (sub.c.completeness, mention_count)
    return tuple(directed(column, direction) for column in pair)
