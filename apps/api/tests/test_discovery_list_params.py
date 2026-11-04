"""Legacy and canonical list parameters on the discovery list routes, pinned before the query refactor (chapter B5)."""

from __future__ import annotations

from app.models.discovery import DiscoverySource, DiscoveryMentionRole, DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _admin_headers, _catalogue, client  # noqa: F401
from test_discovery_admin_list_query import _targets, _task
from test_discovery_candidate_sources_api import SOURCES_URL
from test_discovery_candidates_admin_api import _candidate, _keys, _mention
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401

TASKS_URL = "/api/v1/discovery/admin/tasks"
MACHINE_CANDIDATES_URL = "/api/v1/discovery/machine/candidates"


def test_task_list_accepts_each_legacy_filter_alone(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _task(db_session, catalogue, "queued", status=DiscoveryTaskStatus.PENDING, kind=DiscoveryTaskKind.FETCH_URL)
    _task(db_session, catalogue, "done", status=DiscoveryTaskStatus.COMPLETED, kind=DiscoveryTaskKind.HARVEST_PAYLOAD)

    assert _targets(client, status="completed") == ["done"]
    assert _targets(client, kind="fetch_url") == ["queued"]
    assert _targets(client, source="govdata") == ["queued", "done"]


def test_task_list_rejects_unknown_legacy_status_with_422_and_lists_the_parameter(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _task(db_session, _catalogue(db_session), "one")

    response = client.get(TASKS_URL, params={"status": "bogus"}, headers=_admin_headers())

    assert response.status_code == 422
    assert "status" in response.text


def test_candidate_list_accepts_legacy_role_and_source_alone(client: TestClient[Litestar], db_session: Session) -> None:
    govdata = _catalogue(db_session)
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="svc-2")
    optional_hit = _candidate(db_session, govdata, key="optional-hit")
    _mention(db_session, optional_hit, govdata, role=DiscoveryMentionRole.FORM)
    pvog_hit = _candidate(db_session, pvog, key="pvog-hit")
    _mention(db_session, pvog_hit, pvog)

    assert _keys(client, role="form") == ["optional-hit"]
    assert _keys(client, source="pvog") == ["pvog-hit"]


def test_candidate_sources_rejects_more_than_twenty_service_ids(
    machine_client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)
    ids = [f"00000000-0000-0000-0000-{n:012d}" for n in range(21)]

    response = machine_client.get(SOURCES_URL, params={"catalogue_service_id": ids}, headers={"X-API-Key": key})

    assert response.status_code == 422


def test_machine_candidate_list_rejects_negative_min_mentions(
    machine_client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)

    response = machine_client.get(
        MACHINE_CANDIDATES_URL, params={"min_mentions": -1}, headers={"X-API-Key": key}
    )

    assert response.status_code == 422
