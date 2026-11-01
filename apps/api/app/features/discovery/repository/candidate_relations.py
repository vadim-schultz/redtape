"""The relations one admin candidate query joins: mention statistics and, when needed, the completeness model."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, String, cast, distinct, func, null, select
from sqlalchemy.sql.expression import Subquery

from app.config import settings
from app.features.discovery.repository.candidate_completeness import completeness_subquery
from app.features.discovery.repository.candidate_sort import SortInputs
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate


def mention_stats() -> Subquery:
    """Return ``(candidate_id, mention_count, roles)`` per candidate that has a mention."""
    role = cast(DiscoveryCandidateMention.role, String)
    return (
        select(
            DiscoveryCandidateMention.candidate_id,
            func.count(DiscoveryCandidateMention.id).label("mention_count"),
            func.array_agg(distinct(role)).label("roles"),
        )
        .group_by(DiscoveryCandidateMention.candidate_id)
        .subquery()
    )


def mention_count_of(stats: Subquery) -> ColumnElement[int]:
    """Return the mention count of ``stats``, ``0`` for a candidate without a mention."""
    return func.coalesce(stats.c.mention_count, 0)


def with_stats(stmt: Select, stats: Subquery) -> Select:
    """Left-join ``stats`` to a select over candidates."""
    return stmt.outerjoin(stats, stats.c.candidate_id == DiscoveryDocumentCandidate.id)


@dataclass(frozen=True, slots=True)
class CandidateRelations:
    """Mention statistics plus the completeness read model, which only the queries that use it carry."""

    stats: Subquery
    completeness: Subquery | None = None

    @classmethod
    def with_completeness(cls) -> CandidateRelations:
        """Build the relations including the completeness read model with the settings thresholds."""
        return cls(mention_stats(), completeness_subquery(settings))

    @classmethod
    def mentions_only(cls) -> CandidateRelations:
        """Build the relations of the plain list: no completeness join."""
        return cls(mention_stats())

    @property
    def mention_count(self) -> ColumnElement[int]:
        """The mention count column, ``0`` without a mention."""
        return mention_count_of(self.stats)

    def join(self, stmt: Select) -> Select:
        """Join the relations to a select over candidates."""
        joined = with_stats(stmt, self.stats)
        if self.completeness is None:
            return joined
        return joined.join(self.completeness, self.completeness.c.candidate_id == DiscoveryDocumentCandidate.id)

    def sort_inputs(self) -> SortInputs:
        """Return the columns an ordering may read."""
        completeness = null() if self.completeness is None else self.completeness.c.completeness
        return SortInputs(self.mention_count, self.stats.c.roles, completeness)
