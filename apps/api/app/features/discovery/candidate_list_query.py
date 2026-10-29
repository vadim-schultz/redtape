"""Canonical list-query allowlist of the admin candidate listing and its mapping to a ``CandidateFilter``."""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

from app.features.discovery.repository import CandidateFilter, CandidateSortKey
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryMentionRole, DiscoverySource
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter, min_int_filter

T = TypeVar("T")

CANDIDATE_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in CandidateSortKey),
    filters={
        "status": enum_filter(DiscoveryCandidateStatus),
        "role": enum_filter(DiscoveryMentionRole),
        "source": enum_filter(DiscoverySource),
        "min_mentions": min_int_filter(0),
    },
)


def _canonical_or(canonical: T | None, legacy: T | None) -> T | None:
    return legacy if canonical is None else canonical


def candidate_filter_from(query: ListQuery, legacy: CandidateFilter) -> CandidateFilter:
    """Return the filter for ``query``; canonical parameters win over the ``legacy`` ones they replace."""
    narrowed = replace(
        legacy,
        q=query.q,
        status=_canonical_or(query.filter_value("status", DiscoveryCandidateStatus), legacy.status),
        role=_canonical_or(query.filter_value("role", DiscoveryMentionRole), legacy.role),
        source=_canonical_or(query.filter_value("source", DiscoverySource), legacy.source),
        min_mentions=_canonical_or(query.filter_value("min_mentions", int), legacy.min_mentions),
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=CandidateSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
