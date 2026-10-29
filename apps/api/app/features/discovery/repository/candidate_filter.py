"""Filter options and sort choice for the admin candidate listing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy import ColumnElement, exists, func, literal, select

from app.features.discovery.repository.candidate_sort import (
    CandidateSortKey,
    MentionCount,
    Ordering,
    candidate_ordering,
)
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


def _title_matches(text: str) -> ColumnElement[bool]:
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


def _when(value: T | None, build: Callable[[T], ColumnElement[bool]]) -> list[ColumnElement[bool]]:
    return [] if value is None else [build(value)]


@dataclass(frozen=True, slots=True)
class CandidateFilter:
    """Optional narrowing and ordering of one candidate listing."""

    status: DiscoveryCandidateStatus | None = None
    q: str | None = None
    min_mentions: int | None = None
    role: DiscoveryMentionRole | None = None
    source: DiscoverySource | None = None
    sort_by: CandidateSortKey = CandidateSortKey.MENTIONS
    sort_order: SortOrder = SortOrder.DESC

    def conditions(self, mention_count: MentionCount) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        return [
            *_when(self.status, lambda status: Candidate.status == status),
            *_when(self.q, _title_matches),
            *_when(self.min_mentions, lambda minimum: mention_count >= minimum),
            *_when(self.role, _has_role),
            *_when(self.source, _has_source),
        ]

    def ordering(self, mention_count: MentionCount) -> Ordering:
        """Return the order-by clauses of the chosen sort."""
        return candidate_ordering(self.sort_by, self.sort_order, mention_count)
