"""Canonical list-query allowlist of the admin candidate listing and its mapping to a ``CandidateFilter``."""

from __future__ import annotations

from dataclasses import replace

from app.features.discovery.repository import CandidateFilter, CandidateSortKey
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryMentionRole, DiscoverySource
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter, min_int_filter

CANDIDATE_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in CandidateSortKey),
    filters={
        "status": enum_filter(DiscoveryCandidateStatus),
        "role": enum_filter(DiscoveryMentionRole),
        "source": enum_filter(DiscoverySource),
        "min_mentions": min_int_filter(0),
    },
)


def candidate_filter_from(query: ListQuery, legacy: CandidateFilter) -> CandidateFilter:
    """Return the filter for ``query``; canonical parameters win over the ``legacy`` ones they replace."""
    narrowed = replace(
        legacy,
        q=query.q,
        status=query.filter_or("status", DiscoveryCandidateStatus, legacy.status),
        role=query.filter_or("role", DiscoveryMentionRole, legacy.role),
        source=query.filter_or("source", DiscoverySource, legacy.source),
        min_mentions=query.filter_or("min_mentions", int, legacy.min_mentions),
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=CandidateSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
