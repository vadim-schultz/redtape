"""HTTP behavior of the budget ledger routes (chapter 23)."""

from __future__ import annotations

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _admin_headers
from test_discovery_machine_api import _issue_key

MACHINE = "/api/v1/discovery/machine/budgets"
ADMIN = "/api/v1/discovery/admin/budgets"
RESOURCES = {"r2_class_a", "r2_class_b", "browser_seconds", "neurons", "actions_minutes", "azure_translator_chars"}


def _by_resource(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["resource"]): item for item in items}


def test_list_returns_every_resource_with_its_cap_for_the_machine_key(
    client: TestClient[Litestar], db_session: Session
) -> None:
    key = _issue_key(db_session)

    response = client.get(MACHINE, headers={"X-API-Key": key})

    rows = _by_resource(response.json()["items"])
    assert response.status_code == 200
    assert set(rows) == RESOURCES
    assert (rows["neurons"]["cap"], rows["neurons"]["used"], rows["neurons"]["remaining"]) == (9500, 0, 9500)
    assert rows["actions_minutes"]["cap"] == 1000
    assert rows["azure_translator_chars"]["cap"] == 1_900_000


def test_list_requires_the_machine_key(client: TestClient[Litestar]) -> None:
    assert client.get(MACHINE).status_code == 401
    assert client.get(MACHINE, headers={"X-API-Key": "wrong"}).status_code == 401


def test_azure_translator_chars_reserves_up_to_its_monthly_cap_over_http(
    client: TestClient[Litestar], db_session: Session
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}

    granted = client.post(f"{MACHINE}/azure_translator_chars/reserve", json={"amount": 1_900_000}, headers=headers)
    denied = client.post(f"{MACHINE}/azure_translator_chars/reserve", json={"amount": 1}, headers=headers)

    assert (granted.status_code, granted.json()) == (200, {"granted": True, "remaining": 0})
    assert (denied.status_code, denied.json()) == (409, {"granted": False, "remaining": 0})


def test_reserve_returns_200_when_granted_and_409_when_denied(
    client: TestClient[Litestar], db_session: Session
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}

    granted = client.post(f"{MACHINE}/neurons/reserve", json={"amount": 9000}, headers=headers)
    denied = client.post(f"{MACHINE}/neurons/reserve", json={"amount": 600}, headers=headers)

    assert (granted.status_code, granted.json()) == (200, {"granted": True, "remaining": 500})
    assert (denied.status_code, denied.json()) == (409, {"granted": False, "remaining": 500})


@pytest.mark.parametrize("amount", [0, -1, "NaN", "Infinity", 10**12])
def test_reserve_rejects_an_unusable_amount_with_422(
    client: TestClient[Litestar], db_session: Session, amount: object
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}

    response = client.post(f"{MACHINE}/neurons/reserve", json={"amount": amount}, headers=headers)

    assert response.status_code == 422
    rows = _by_resource(client.get(MACHINE, headers=headers).json()["items"])
    assert rows["neurons"]["used"] == 0


def test_reserve_rejects_an_unknown_resource_with_404(client: TestClient[Litestar], db_session: Session) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}

    assert client.post(f"{MACHINE}/bananas/reserve", json={"amount": 1}, headers=headers).status_code == 404
    assert client.post(f"{MACHINE}/bananas/exhaust", headers=headers).status_code == 404
    assert client.post(f"{MACHINE}/bananas/adjust", json={"delta": 1}, headers=headers).status_code == 404


def test_adjust_and_exhaust_update_the_snapshot(client: TestClient[Litestar], db_session: Session) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}
    client.post(f"{MACHINE}/browser_seconds/reserve", json={"amount": 100}, headers=headers)

    adjusted = client.post(f"{MACHINE}/browser_seconds/adjust", json={"delta": -40.5}, headers=headers)
    exhausted = client.post(f"{MACHINE}/browser_seconds/exhaust", headers=headers)
    after = client.post(f"{MACHINE}/browser_seconds/reserve", json={"amount": 1}, headers=headers)

    assert adjusted.status_code == 200
    assert (adjusted.json()["used"], adjusted.json()["exhausted"]) == (59.5, False)
    assert (exhausted.json()["used"], exhausted.json()["exhausted"]) == (59.5, True)
    assert after.status_code == 409


def test_adjust_rejects_a_non_finite_delta_with_422(client: TestClient[Litestar], db_session: Session) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}

    assert client.post(f"{MACHINE}/neurons/adjust", json={"delta": "NaN"}, headers=headers).status_code == 422


def test_admin_budgets_include_the_stored_bytes_and_the_byte_cap(
    client: TestClient[Litestar], db_session: Session
) -> None:
    response = client.get(ADMIN, headers=_admin_headers())

    body = response.json()
    assert response.status_code == 200
    assert {item["resource"] for item in body["items"]} == RESOURCES
    assert (body["stored_bytes"], body["stored_bytes_cap"]) == (0, 9_500_000_000)


def test_admin_budgets_require_an_admin(client: TestClient[Litestar], db_session: Session) -> None:
    key = _issue_key(db_session)

    assert client.get(ADMIN).status_code == 401
    assert client.get(ADMIN, headers={"X-API-Key": key}).status_code == 401
