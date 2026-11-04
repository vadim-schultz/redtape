"""Unit tests for the discovery list query providers: legacy-to-canonical overlay without HTTP (chapter B5)."""

from __future__ import annotations

from app.features.discovery.candidate_list_query import provide_candidate_query, provide_machine_candidate_query
from app.features.discovery.catalogue_list_query import provide_catalogue_query
from app.features.discovery.repository import CandidateSort, CandidateSortKey, Page
from app.features.discovery.task_list_query import provide_task_query
from app.models.discovery import DiscoveryCandidateStatus, DiscoverySource, DiscoveryTaskStatus
from app.shared.list_query import ListQuery, SortOrder
from app.shared.paging import PageParams

PAGE = PageParams(offset=10, limit=5)


def _legacy(**overrides: object) -> dict[str, object]:
    """Every legacy candidate parameter at its default, with ``overrides`` applied."""
    defaults: dict[str, object] = {
        "status": None,
        "min_mentions": None,
        "role": None,
        "source": None,
        "sort": CandidateSort.MENTIONS_DESC,
    }
    return defaults | overrides


def test_provide_candidate_query_translates_legacy_sort_and_lets_canonical_win() -> None:
    canonical = ListQuery(sort_by="title", sort_order=SortOrder.DESC, q="ausweis")

    legacy_only = provide_candidate_query(PAGE, ListQuery(), **_legacy(sort=CandidateSort.TITLE_ASC))
    canonical_wins = provide_candidate_query(PAGE, canonical, **_legacy(sort=CandidateSort.TITLE_ASC))

    assert legacy_only.filters.sort_by is CandidateSortKey.TITLE
    assert legacy_only.filters.sort_order is SortOrder.ASC
    assert canonical_wins.filters.sort_by is CandidateSortKey.TITLE
    assert canonical_wins.filters.sort_order is SortOrder.DESC
    assert canonical_wins.filters.q == "ausweis"
    assert canonical_wins.page == Page(offset=10, limit=5)


def test_provide_candidate_query_prefers_canonical_status_over_legacy() -> None:
    query = ListQuery(filters={"status": DiscoveryCandidateStatus.EMITTED})

    built = provide_candidate_query(PAGE, query, **_legacy(status=DiscoveryCandidateStatus.STAGED))

    assert built.filters.status is DiscoveryCandidateStatus.EMITTED


def test_provide_machine_candidate_query_has_no_list_query_and_keeps_legacy_filters() -> None:
    built = provide_machine_candidate_query(PAGE, status=DiscoveryCandidateStatus.STAGED, min_mentions=2)

    assert built.filters.status is DiscoveryCandidateStatus.STAGED
    assert built.filters.min_mentions == 2
    assert built.page == Page(offset=10, limit=5)


def test_provide_task_query_lets_canonical_status_win_over_legacy() -> None:
    query = ListQuery(filters={"status": DiscoveryTaskStatus.COMPLETED})

    built = provide_task_query(PAGE, query, status=DiscoveryTaskStatus.PENDING)

    assert built.filters.status is DiscoveryTaskStatus.COMPLETED
    assert built.page == Page(offset=10, limit=5)


def test_provide_catalogue_query_lets_canonical_source_win_over_legacy() -> None:
    query = ListQuery(filters={"source": DiscoverySource.PVOG})

    built = provide_catalogue_query(PAGE, query, source=DiscoverySource.GOVDATA)

    assert built.filters.source is DiscoverySource.PVOG
    assert built.page == Page(offset=10, limit=5)
