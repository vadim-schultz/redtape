"""The public list route throttles searches (requests with ``q``) per client address (chapter 8, O12)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.config import settings
from app.features.search.rate_limit import client_address
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from query_embedder_support import FakeQueryEmbedder
from search_api_fixtures import URL, serve_with


@pytest.fixture
def limited(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    """A client of an app whose search limit is two requests a minute."""
    monkeypatch.setattr(settings, "search_rate_limit_per_minute", 2)
    with serve_with(monkeypatch, db_session, FakeQueryEmbedder()) as client:
        yield client


def forwarded(address: str) -> dict[str, str]:
    return {"X-Forwarded-For": address}


def test_exceeding_the_limit_answers_429(limited: TestClient[Litestar]) -> None:
    statuses = [limited.get(URL, params={"q": "kindergeld"}).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]


def test_browse_requests_are_not_throttled(limited: TestClient[Litestar]) -> None:
    statuses = [limited.get(URL).status_code for _ in range(5)]

    assert statuses == [200] * 5


def test_each_client_address_has_its_own_allowance(limited: TestClient[Litestar]) -> None:
    for _ in range(2):
        limited.get(URL, params={"q": "kindergeld"}, headers=forwarded("203.0.113.1"))

    blocked = limited.get(URL, params={"q": "kindergeld"}, headers=forwarded("203.0.113.1"))
    other = limited.get(URL, params={"q": "kindergeld"}, headers=forwarded("203.0.113.2"))

    assert (blocked.status_code, other.status_code) == (429, 200)


def test_a_spoofed_leading_forwarded_for_entry_does_not_reset_the_allowance(limited: TestClient[Litestar]) -> None:
    for number in range(2):
        limited.get(URL, params={"q": "kindergeld"}, headers=forwarded(f"198.51.100.{number}, 203.0.113.9"))

    response = limited.get(URL, params={"q": "kindergeld"}, headers=forwarded("198.51.100.77, 203.0.113.9"))

    assert response.status_code == 429


@pytest.mark.parametrize(
    ("header", "hops", "expected"),
    [
        ("1.1.1.1, 2.2.2.2", 1, "2.2.2.2"),
        ("1.1.1.1, 2.2.2.2", 2, "1.1.1.1"),
        ("1.1.1.1", 2, "1.1.1.1"),
        ("1.1.1.1, 2.2.2.2", 0, "peer"),
        (None, 1, "peer"),
        ("", 1, "peer"),
    ],
)
def test_the_client_is_the_forwarded_entry_the_configured_hops_from_the_right(
    header: str | None, hops: int, expected: str
) -> None:
    assert client_address(header, "peer", hops) == expected
