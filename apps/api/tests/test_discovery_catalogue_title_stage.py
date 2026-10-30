"""Title sort, stage filter and unfiltered summary of the admin catalogue list."""

from __future__ import annotations

import pytest
from app.features.discovery.repository import CatalogueRepository
from app.models.discovery import CatalogueService, DiscoverySource
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import CATALOGUE_URL, _admin_headers, _catalogue

Params = dict[str, object]


def _row(
    session: Session, external_id: str, *, title: dict[str, str], stage: str = "T0", source: str = "govdata"
) -> CatalogueService:
    row = _catalogue(session, source=DiscoverySource(source), external_id=external_id)
    row.title_i18n = title
    row.pipeline_stage = stage
    session.flush()
    return row


def _ids(client: TestClient[Litestar], params: Params) -> list[str]:
    body = client.get(CATALOGUE_URL, params=params, headers=_admin_headers()).json()
    return [item["external_id"] for item in body["items"]]


def _seed_titles(session: Session) -> None:
    _row(session, "c-zeta", title={"de": "Zeta"})
    _row(session, "a-alpha", title={"de": "alpha"})
    _row(session, "b-beta", title={"en": "Beta"})
    _row(session, "d-twin-1", title={"de": "Twin"})
    _row(session, "e-twin-2", title={"de": "Twin"})
    _row(session, "0-untitled", title={})


def test_catalogue_api_sorts_by_title_and_breaks_ties_deterministically(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _seed_titles(db_session)

    ascending = _ids(client, {"sort_by": "title", "sort_order": "asc"})
    descending = _ids(client, {"sort_by": "title", "sort_order": "desc"})

    assert ascending[:3] == ["0-untitled", "a-alpha", "b-beta"]
    assert ascending[-1] == "c-zeta"
    assert set(ascending[3:5]) == {"d-twin-1", "e-twin-2"}
    assert descending[0] == "c-zeta"
    assert descending[-1] == "0-untitled"
    assert ascending == _ids(client, {"sort_by": "title", "sort_order": "asc"})


def test_catalogue_api_title_sort_is_stable_across_pages(client: TestClient[Litestar], db_session: Session) -> None:
    _seed_titles(db_session)
    params: Params = {"sort_by": "title", "sort_order": "asc", "limit": 2}

    pages = [_ids(client, {**params, "offset": offset}) for offset in (0, 2, 4)]

    assert [len(page) for page in pages] == [2, 2, 2]
    assert [item for page in pages for item in page] == _ids(client, {"sort_by": "title", "sort_order": "asc"})


def test_catalogue_api_filters_by_stage_and_totals_the_filtered_result(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _row(db_session, "done-1", title={"de": "A"}, stage="T4")
    _row(db_session, "done-2", title={"de": "B"}, stage="T4")
    _row(db_session, "fresh", title={"de": "C"}, stage="T0")

    body = client.get(CATALOGUE_URL, params={"filter[stage]": "T4"}, headers=_admin_headers()).json()

    assert sorted(item["external_id"] for item in body["items"]) == ["done-1", "done-2"]
    assert {item["pipeline_stage"] for item in body["items"]} == {"T4"}
    assert body["total"] == 2


def test_catalogue_api_rejects_an_unknown_stage_before_querying(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    queried: list[str] = []
    monkeypatch.setattr(CatalogueRepository, "count_catalogue", lambda *_: queried.append("count") or 0)
    monkeypatch.setattr(CatalogueRepository, "list_catalogue_page", lambda *_, **__: queried.append("page") or [])

    response = client.get(CATALOGUE_URL, params={"filter[stage]": "T9"}, headers=_admin_headers())

    assert response.status_code == 422
    assert [error["key"] for error in response.json()["extra"]] == ["filter[stage]"]
    assert queried == []


def test_catalogue_api_summary_counts_the_unfiltered_catalogue(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _row(db_session, "gov-t4", title={"de": "A"}, stage="T4")
    _row(db_session, "gov-t0", title={"de": "B"}, stage="T0")
    _row(db_session, "pvog-t0", title={"de": "C"}, stage="T0", source="pvog")

    body = client.get(
        CATALOGUE_URL, params={"filter[stage]": "T4", "filter[source]": "govdata"}, headers=_admin_headers()
    ).json()

    assert body["total"] == 1
    assert body["summary"] == {
        "total": 3,
        "by_source": {"govdata": 2, "pvog": 1},
        "by_pipeline_stage": {"T0": 2, "T4": 1},
    }
