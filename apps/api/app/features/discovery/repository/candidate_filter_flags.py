"""Filters of the admin candidate list that read the completeness model: the flags and the accepted tag codes."""

from __future__ import annotations

from dataclasses import astuple, dataclass

from sqlalchemy import ColumnElement, String, any_, literal
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.candidate_completeness_flags import FLAG_NAMES

FLAG_FILTERS = (*FLAG_NAMES, "complete")


def accepted(code: str, accepted_codes: ColumnElement) -> ColumnElement[bool]:
    """Return a predicate that ``code`` is one of the accepted codes array (a ``NULL`` array accepts nothing)."""
    return literal(code, String) == any_(accepted_codes)


@dataclass(frozen=True, slots=True)
class CompletenessFilter:
    """Optional yes/no filters on the five flags and on ``complete``, and accepted domain and situation codes."""

    complete: bool | None = None
    has_domain: bool | None = None
    has_situation: bool | None = None
    has_edges: bool | None = None
    has_snapshot: bool | None = None
    has_screenshot: bool | None = None
    domain: str | None = None
    situation: str | None = None

    @property
    def is_set(self) -> bool:
        """Whether any filter is set, so the query has to join the completeness model."""
        return any(value is not None for value in astuple(self))

    def conditions(self, completeness: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        return [*self._flag_conditions(completeness), *self._code_conditions(completeness)]

    def _flag_conditions(self, completeness: Subquery) -> list[ColumnElement[bool]]:
        wanted = ((name, getattr(self, name)) for name in FLAG_FILTERS)
        return [completeness.c[name].is_(value) for name, value in wanted if value is not None]

    def _code_conditions(self, completeness: Subquery) -> list[ColumnElement[bool]]:
        pairs = (
            (self.domain, completeness.c.accepted_domain_codes),
            (self.situation, completeness.c.accepted_situation_codes),
        )
        return [accepted(code, codes) for code, codes in pairs if code is not None]
