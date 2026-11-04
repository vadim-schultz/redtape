"""Canonical list-query allowlist of the admin candidate listing and its mapping to a ``CandidateFilter``."""

from __future__ import annotations

import enum
from dataclasses import replace
from uuid import UUID

from litestar.params import Parameter

from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import (
    LEGACY_SORTS,
    CandidateFilter,
    CandidateSort,
    CandidateSortKey,
    Page,
)
from app.features.discovery.repository.candidate_filter_flags import FLAG_FILTERS, CompletenessFilter
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryMentionRole, DiscoverySource
from app.shared.list_query import (
    ListQuery,
    ListQuerySpec,
    SortOrder,
    enum_filter,
    min_int_filter,
    text_filter,
    uuid_filter,
)
from app.shared.paging import PageParams

CODE_MAX_LENGTH = 64


class FlagChoice(enum.StrEnum):
    """Values of the yes/no flag filters."""

    YES = "yes"
    NO = "no"


CANDIDATE_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in CandidateSortKey),
    filters={
        "status": enum_filter(DiscoveryCandidateStatus),
        "role": enum_filter(DiscoveryMentionRole),
        "source": enum_filter(DiscoverySource),
        "min_mentions": min_int_filter(0),
        "jurisdiction": uuid_filter,
        "domain": text_filter(CODE_MAX_LENGTH),
        "situation": text_filter(CODE_MAX_LENGTH),
        **{name: enum_filter(FlagChoice) for name in FLAG_FILTERS},
    },
)


def _flag(query: ListQuery, name: str) -> bool | None:
    choice = query.filter_value(name, FlagChoice)
    return None if choice is None else choice is FlagChoice.YES


def _completeness_from(query: ListQuery) -> CompletenessFilter:
    flags = {name: _flag(query, name) for name in FLAG_FILTERS}
    domain, situation = query.filter_value("domain", str), query.filter_value("situation", str)
    return CompletenessFilter(**flags, domain=domain, situation=situation)


def _jurisdiction_from(query: ListQuery) -> UUID | None:
    raw = query.filter_value("jurisdiction", str)
    return None if raw is None else UUID(raw)


def provide_candidate_query(
    page: PageParams,
    list_query: ListQuery,
    status: DiscoveryCandidateStatus | None = Parameter(query="status", default=None),
    min_mentions: int | None = Parameter(query="min_mentions", default=None, ge=0),
    role: DiscoveryMentionRole | None = Parameter(query="role", default=None),
    source: DiscoverySource | None = Parameter(query="source", default=None),
    sort: CandidateSort = Parameter(query="sort", default=CandidateSort.MENTIONS_DESC),
) -> DiscoveryListQuery[CandidateFilter]:
    """Collect the admin candidate list parameters, legacy and canonical, into one filter and page."""
    sort_by, sort_order = LEGACY_SORTS[sort]
    legacy = CandidateFilter(
        status=status, min_mentions=min_mentions, role=role, source=source, sort_by=sort_by, sort_order=sort_order
    )
    candidate_filter = candidate_filter_from(list_query, legacy)
    return DiscoveryListQuery(filters=candidate_filter, page=Page(offset=page.offset, limit=page.limit))


def provide_machine_candidate_query(
    page: PageParams,
    status: DiscoveryCandidateStatus | None = Parameter(query="status", default=None),
    min_mentions: int | None = Parameter(query="min_mentions", default=None, ge=0),
) -> DiscoveryListQuery[CandidateFilter]:
    """Collect the machine candidate list parameters into one filter and page."""
    candidate_filter = CandidateFilter(status=status, min_mentions=min_mentions)
    return DiscoveryListQuery(filters=candidate_filter, page=Page(offset=page.offset, limit=page.limit))


def candidate_filter_from(query: ListQuery, legacy: CandidateFilter) -> CandidateFilter:
    """Return the filter for ``query``; canonical parameters win over the ``legacy`` ones they replace."""
    narrowed = replace(
        legacy,
        q=query.q,
        status=query.filter_or("status", DiscoveryCandidateStatus, legacy.status),
        role=query.filter_or("role", DiscoveryMentionRole, legacy.role),
        source=query.filter_or("source", DiscoverySource, legacy.source),
        min_mentions=query.filter_or("min_mentions", int, legacy.min_mentions),
        jurisdiction_id=_jurisdiction_from(query),
        completeness=_completeness_from(query),
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=CandidateSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
