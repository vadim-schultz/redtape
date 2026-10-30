"""Canonical list query (``sort_by``, ``q``, ``filter[...]``) on the admin task and catalogue lists."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from app.features.discovery.repository import CatalogueRepository, TaskListingRepository
from app.models.discovery import (
    CatalogueService,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import CATALOGUE_URL, TASKS_URL, _admin_headers, _catalogue

Params = dict[str, object]
_CLOCK = itertools.count()


def _task(
    session: Session,
    catalogue: CatalogueService,
    target: str,
    *,
    kind: DiscoveryTaskKind = DiscoveryTaskKind.FETCH_URL,
    status: DiscoveryTaskStatus = DiscoveryTaskStatus.PENDING,
    **fields: object,
) -> DiscoveryTask:
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=kind,
        target_url=f"https://example.gov/{target}",
        status=status,
        created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=next(_CLOCK)),
        **fields,
    )
    session.add(task)
    session.flush()
    return task


def _targets(client: TestClient[Litestar], **params: object) -> list[str]:
    body = client.get(TASKS_URL, params=params, headers=_admin_headers()).json()
    return [item["target_url"].rsplit("/", 1)[1] for item in body["items"]]


def _external_ids(client: TestClient[Litestar], params: Params) -> list[str]:
    body = client.get(CATALOGUE_URL, params=params, headers=_admin_headers()).json()
    return [item["external_id"] for item in body["items"]]


def test_task_list_query_sorts_by_an_allowlisted_key_in_both_directions(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    _task(db_session, catalogue, "two", attempt_count=2)
    _task(db_session, catalogue, "zero", attempt_count=0)
    _task(db_session, catalogue, "five", attempt_count=5)

    assert _targets(client, sort_by="attempts", sort_order="desc") == ["five", "two", "zero"]
    assert _targets(client, sort_by="attempts", sort_order="asc") == ["zero", "two", "five"]
    assert _targets(client, sort_by="target", sort_order="asc") == ["five", "two", "zero"]


def test_task_list_query_orders_ties_by_the_queue_order_so_pages_do_not_oscillate(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    for target in ("d", "a", "c", "b"):
        _task(db_session, catalogue, target, kind=DiscoveryTaskKind.FETCH_URL)
    params = {"sort_by": "kind", "sort_order": "asc", "limit": 2}

    first = _targets(client, **params)
    again = _targets(client, **params)
    next_page = _targets(client, **params, offset=2)

    assert first == again == ["d", "a"]
    assert next_page == ["c", "b"]


def test_task_list_query_filters_by_status_source_and_kind_with_a_consistent_total(
    client: TestClient[Litestar], db_session: Session
) -> None:
    govdata = _catalogue(db_session)
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="svc-2")
    _task(db_session, govdata, "gov-pending")
    _task(db_session, govdata, "gov-failed", status=DiscoveryTaskStatus.FAILED)
    _task(db_session, pvog, "pvog-harvest", kind=DiscoveryTaskKind.HARVEST_PAYLOAD)

    body = client.get(TASKS_URL, params={"filter[source]": "govdata", "limit": 1}, headers=_admin_headers()).json()

    assert body["total"] == 2 and len(body["items"]) == 1
    assert _targets(client, **{"filter[status]": "failed"}) == ["gov-failed"]
    assert _targets(client, **{"filter[kind]": "harvest_payload"}) == ["pvog-harvest"]


def test_task_list_query_searches_the_target_literally(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _task(db_session, catalogue, "form%20a")
    _task(db_session, catalogue, "formular")

    assert _targets(client, q="form%") == ["form%20a"]
    assert _targets(client, q="FORM") == ["form%20a", "formular"]
    assert _targets(client, q="absent") == []


def test_task_list_query_beats_the_legacy_filters_it_replaces(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    _task(db_session, catalogue, "pending")
    _task(db_session, catalogue, "failed", status=DiscoveryTaskStatus.FAILED)

    assert _targets(client, status="pending", **{"filter[status]": "failed"}) == ["failed"]
    assert _targets(client, status="pending") == ["pending"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("sort_by", "last_error"),
        ("sort_order", "up"),
        ("filter[status]", "gone"),
        ("filter[kind]", "bogus"),
        ("filter[priority]", "1"),
        ("q", ""),
    ],
)
def test_task_list_query_rejects_values_outside_the_allowlist_before_querying(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    queried: list[str] = []
    monkeypatch.setattr(TaskListingRepository, "count_tasks", lambda *_: queried.append("count") or 0)
    monkeypatch.setattr(TaskListingRepository, "list_tasks_page", lambda *_: queried.append("page") or [])
    params = {"sort_by": "kind", key: value} if key == "sort_order" else {key: value}

    response = client.get(TASKS_URL, params=params, headers=_admin_headers())

    assert response.status_code == 422
    assert [error["key"] for error in response.json()["extra"]] == [key]
    assert queried == []


def test_catalogue_list_query_sorts_filters_and_searches_with_a_consistent_total(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="b-gov")
    _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="a-gov")
    _catalogue(db_session, source=DiscoverySource.PVOG, external_id="c-pvog")

    ordered = client.get(
        CATALOGUE_URL,
        params={"sort_by": "external_id", "sort_order": "desc", "filter[source]": "govdata"},
        headers=_admin_headers(),
    ).json()

    assert [item["external_id"] for item in ordered["items"]] == ["b-gov", "a-gov"]
    assert (ordered["total"], ordered["summary"]["total"]) == (2, 3)
    assert _external_ids(client, {"q": "PVOG"}) == ["c-pvog"]
    assert _external_ids(client, {"sort_by": "source", "sort_order": "desc"})[0] == "c-pvog"


def test_catalogue_list_query_pages_past_the_first_page_in_a_stable_order(
    client: TestClient[Litestar], db_session: Session
) -> None:
    for index in range(5):
        _catalogue(db_session, external_id=f"svc-{index}")
    params: Params = {"sort_by": "stage", "sort_order": "asc", "limit": 2}

    pages = [_external_ids(client, {**params, "offset": offset}) for offset in (0, 2, 4)]
    body = client.get(CATALOGUE_URL, params=params, headers=_admin_headers()).json()

    assert [len(page) for page in pages] == [2, 2, 1]
    assert len({item for page in pages for item in page}) == 5
    assert pages == [_external_ids(client, {**params, "offset": offset}) for offset in (0, 2, 4)]
    assert body["total"] == 5


def test_catalogue_list_query_keeps_the_legacy_source_parameter_and_lets_the_canonical_one_win(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="gov-1")
    _catalogue(db_session, source=DiscoverySource.PVOG, external_id="pvog-1")

    assert _external_ids(client, {"source": "govdata"}) == ["gov-1"]
    assert _external_ids(client, {"source": "govdata", "filter[source]": "pvog"}) == ["pvog-1"]


@pytest.mark.parametrize(
    ("key", "value"),
    [("sort_by", "raw_payload"), ("filter[source]", "unknown"), ("filter[stage]", "T9"), ("q", "x" * 201)],
)
def test_catalogue_list_query_rejects_values_outside_the_allowlist_before_querying(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    queried: list[str] = []
    monkeypatch.setattr(CatalogueRepository, "count_catalogue", lambda *_: queried.append("count") or 0)
    monkeypatch.setattr(CatalogueRepository, "list_catalogue_page", lambda *_, **__: queried.append("page") or [])

    response = client.get(CATALOGUE_URL, params={key: value}, headers=_admin_headers())

    assert response.status_code == 422
    assert [error["key"] for error in response.json()["extra"]] == [key]
    assert queried == []
