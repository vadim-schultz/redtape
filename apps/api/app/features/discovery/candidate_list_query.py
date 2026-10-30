"""Canonical list-query allowlist of the admin candidate listing and its mapping to a ``CandidateFilter``."""

from __future__ import annotations

import enum
from dataclasses import replace
from uuid import UUID

from app.features.discovery.repository import CandidateFilter, CandidateSortKey
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
