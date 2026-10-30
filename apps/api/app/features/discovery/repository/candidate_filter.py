"""Filter options and sort choice for the admin candidate listing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, literal, select

from app.features.discovery.repository.candidate_filter_flags import CompletenessFilter
from app.features.discovery.repository.candidate_relations import CandidateRelations
from app.features.discovery.repository.candidate_sort import CandidateSortKey, Ordering, ordered_by
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
    DiscoverySource,
)
from app.shared.list_query import SortOrder

Candidate = DiscoveryDocumentCandidate
Mention = DiscoveryCandidateMention
T = TypeVar("T")


def title_matches(text: str) -> ColumnElement[bool]:
    """Return a predicate matching ``text`` against the title in any locale."""
    titles = func.jsonb_each_text(Candidate.title_i18n).table_valued("value")
    return exists(select(literal(1)).select_from(titles).where(titles.c.value.icontains(text, autoescape=True)))


def _mentioned(*conditions: ColumnElement[bool]) -> ColumnElement[bool]:
    """Return a predicate for a mention of the candidate that satisfies ``conditions``."""
    mentions = select(literal(1)).select_from(Mention).where(Mention.candidate_id == Candidate.id, *conditions)
    return exists(mentions.join(CatalogueService, Mention.catalogue_service_id == CatalogueService.id))


def _has_role(role: DiscoveryMentionRole) -> ColumnElement[bool]:
    return _mentioned(Mention.role == role)


def _has_source(source: DiscoverySource) -> ColumnElement[bool]:
    return _mentioned(CatalogueService.source == source)


def when(value: T | None, build: Callable[[T], ColumnElement[bool]]) -> list[ColumnElement[bool]]:
    """Return ``[build(value)]`` when ``value`` is set, else no where-clause."""
    return [] if value is None else [build(value)]


@dataclass(frozen=True, slots=True)
class CandidateFilter:
    """Optional narrowing and ordering of one candidate listing."""

    status: DiscoveryCandidateStatus | None = None
    q: str | None = None
    min_mentions: int | None = None
    role: DiscoveryMentionRole | None = None
    source: DiscoverySource | None = None
    jurisdiction_id: UUID | None = None
    completeness: CompletenessFilter = CompletenessFilter()
    sort_by: CandidateSortKey = CandidateSortKey.MENTIONS
    sort_order: SortOrder = SortOrder.DESC

    @property
    def needs_completeness(self) -> bool:
        """Whether the query has to join the completeness model: a flag or code filter, or its sort."""
        return self.completeness.is_set or self.sort_by is CandidateSortKey.COMPLETENESS

    def relations(self) -> CandidateRelations:
        """Return the relations this filter reads; the completeness model only when it is needed."""
        if self.needs_completeness:
            return CandidateRelations.with_completeness()
        return CandidateRelations.mentions_only()

    def conditions(self, relations: CandidateRelations) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        return [
            *when(self.status, lambda status: Candidate.status == status),
            *when(self.q, title_matches),
            *when(self.min_mentions, lambda minimum: relations.mention_count >= minimum),
            *when(self.role, _has_role),
            *when(self.source, _has_source),
            *when(self.jurisdiction_id, lambda jurisdiction: Candidate.jurisdiction_id == jurisdiction),
            *self._completeness_conditions(relations),
        ]

    def ordering(self, relations: CandidateRelations) -> Ordering:
        """Return the order-by clauses of the chosen sort."""
        return ordered_by(self.sort_by, self.sort_order, relations.sort_inputs())

    def _completeness_conditions(self, relations: CandidateRelations) -> list[ColumnElement[bool]]:
        if relations.completeness is None:
            return []
        return self.completeness.conditions(relations.completeness)
