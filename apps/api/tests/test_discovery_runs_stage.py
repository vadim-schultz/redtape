"""Run stage and spend on the discovery machine run routes: every drain names its stage and what it spent."""

from __future__ import annotations

import uuid
from typing import get_args

import pytest
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryRun
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session
from test_discovery_run import RUNS_URL, _finish_body, client, headers  # noqa: F401


def _start_with(client: TestClient[Litestar], headers: dict[str, str], body: dict[str, object]) -> str:
    response = client.post(RUNS_URL, json=body, headers=headers)
    assert response.status_code == 201
    return str(response.json()["id"])


def _stored(db_session: Session, run_id: str) -> DiscoveryRun:
    run = DiscoveryRepository(db_session).get_run(uuid.UUID(run_id))
    assert run is not None
    return run


def test_a_drain_run_records_the_stage_it_was_opened_for(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """stage · a run opened for the embed drain stores stage embed, not the kind."""
    run_id = _start_with(client, headers, {"kind": "worker_drain", "stage": "embed"})

    assert _stored(db_session, run_id).stage == "embed"


@pytest.mark.parametrize("stage", ["translate", "snapshot_translate", "worker_drain"])
def test_each_drain_stage_is_accepted(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str], stage: str
) -> None:
    """stage · translate, snapshot_translate and worker_drain are the stages a drain can name."""
    run_id = _start_with(client, headers, {"kind": "worker_drain", "stage": stage})

    assert _stored(db_session, run_id).stage == stage


def test_a_run_opened_without_a_stage_is_recorded_as_a_worker_drain(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """stage · a start that names no stage defaults to its kind, so old callers keep their meaning."""
    run_id = _start_with(client, headers, {"kind": "worker_drain"})

    assert _stored(db_session, run_id).stage == "worker_drain"


def test_an_unknown_stage_is_rejected_with_422(client: TestClient[Litestar], headers: dict[str, str]) -> None:
    """stage · a stage the flow does not know is a validation error, and no run is opened."""
    response = client.post(RUNS_URL, json={"kind": "worker_drain", "stage": "coffee"}, headers=headers)

    assert response.status_code == 422


def test_spend_round_trips_through_the_finish_route(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """spend · the dict the drain reports is stored on the run and read back unchanged."""
    run_id = _start_with(client, headers, {"kind": "worker_drain", "stage": "embed"})
    spend = {"browser_seconds": 12.5, "neurons": 40.0, "azure_translator_chars": 0.0}

    response = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(spend=spend), headers=headers)

    assert response.status_code == 200
    assert _stored(db_session, run_id).spend == spend


def test_a_run_finished_without_spend_stores_none(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """spend · spend is optional: a finish that names none leaves the column empty."""
    run_id = _start_with(client, headers, {"kind": "worker_drain"})

    client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(), headers=headers)

    assert _stored(db_session, run_id).spend is None


def test_an_unknown_resource_in_spend_is_rejected_with_422(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """spend · a resource the ledger does not guard is rejected, and the run stays running."""
    run_id = _start_with(client, headers, {"kind": "worker_drain"})

    response = client.post(
        f"{RUNS_URL}/{run_id}/finish", json=_finish_body(spend={"coffee_beans": 1.0}), headers=headers
    )

    assert response.status_code == 422
    assert _stored(db_session, run_id).status == "running"


def test_a_negative_spend_is_rejected_with_422(client: TestClient[Litestar], headers: dict[str, str]) -> None:
    """spend · a negative amount is not a spend."""
    run_id = _start_with(client, headers, {"kind": "worker_drain"})

    response = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(spend={"neurons": -1.0}), headers=headers)

    assert response.status_code == 422


def test_the_spend_resources_are_the_budget_ledger_resources() -> None:
    """spend · the names a run may report are exactly the resources the budget ledger guards."""
    from app.schema.discovery.machine import SpendResource

    assert set(get_args(SpendResource)) == {resource.value for resource in BudgetResource}
