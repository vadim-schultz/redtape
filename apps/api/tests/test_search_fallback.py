"""Every embedder problem degrades to keyword-only search with a 200, never to an error (chapter 8)."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.cloudflare_embedder import CloudflareQueryEmbedder
from app.features.search.embedder_budget import BudgetedQueryEmbedder, LedgerReservation
from app.features.search.query_embedder import QueryEmbedder, UnavailableQueryEmbedder
from sqlalchemy.orm import Session

from query_embedder_support import ACCOUNT, TOKEN, FakeQueryEmbedder, ScriptedWorkersAi
from search_api_fixtures import URL, serve_with
from search_query_world import indexed, query_vector


def timing_out() -> QueryEmbedder:
    def respond(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    return CloudflareQueryEmbedder(ACCOUNT, TOKEN, "m", dim=3, timeout_s=0.1, http=ScriptedWorkersAi(respond).client())


def erroring() -> QueryEmbedder:
    http = ScriptedWorkersAi(lambda _request: httpx.Response(500, text="boom")).client()
    return CloudflareQueryEmbedder(ACCOUNT, TOKEN, "m", dim=3, timeout_s=0.1, http=http)


def exhausted_budget(session: Session) -> QueryEmbedder:
    now = datetime.now(UTC)
    BudgetService(DiscoveryRepository(session)).exhaust(BudgetResource.NEURONS, now)
    inner = FakeQueryEmbedder({"kindergeld": query_vector()})
    return BudgetedQueryEmbedder(inner, LedgerReservation(lambda: nullcontext(session), Decimal("0.1")))


def working(session: Session) -> QueryEmbedder:
    return FakeQueryEmbedder({"kindergeld": query_vector()})


PROBLEMS: dict[str, Callable[[Session], QueryEmbedder]] = {
    "timeout": lambda _session: timing_out(),
    "error": lambda _session: erroring(),
    "missing-token": lambda _session: UnavailableQueryEmbedder(),
    "exhausted-budget": exhausted_budget,
    "embedder-returns-none": lambda _session: FakeQueryEmbedder(),
}


@pytest.mark.parametrize("problem", PROBLEMS)
def test_an_embedder_problem_returns_200_with_keyword_search(
    problem: str, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    indexed(db_session, "Kindergeld Antrag")
    indexed(db_session, "Semantic only", similarity=0.9)
    embedder = PROBLEMS[problem](db_session)

    with serve_with(monkeypatch, db_session, embedder) as client:
        response = client.get(URL, params={"q": "kindergeld"})

    body = response.json()
    assert response.status_code == 200
    assert body["search_mode"] == "keyword"
    assert [item["title"] for item in body["items"]] == ["Kindergeld Antrag"]
    assert all(item["similarity"] is None for item in body["items"])


def test_a_working_embedder_with_a_granted_budget_is_hybrid(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    indexed(db_session, "Kindergeld Antrag")
    indexed(db_session, "Semantic only", similarity=0.9)
    reserving = BudgetedQueryEmbedder(
        working(db_session), LedgerReservation(lambda: nullcontext(db_session), Decimal("0.1"))
    )

    with serve_with(monkeypatch, db_session, reserving) as client:
        body = client.get(URL, params={"q": "kindergeld"}).json()

    assert body["search_mode"] == "hybrid"
    assert sorted(item["title"] for item in body["items"]) == ["Kindergeld Antrag", "Semantic only"]


def test_an_exhausted_ledger_is_left_untouched_by_the_refused_search(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    indexed(db_session, "Kindergeld Antrag")
    embedder = exhausted_budget(db_session)
    status = BudgetService(DiscoveryRepository(db_session)).status
    before = status(BudgetResource.NEURONS, datetime.now(UTC)).used

    with serve_with(monkeypatch, db_session, embedder) as client:
        client.get(URL, params={"q": "kindergeld"})

    assert status(BudgetResource.NEURONS, datetime.now(UTC)).used == before


def test_a_database_error_while_reserving_does_not_fail_the_search(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import OperationalError

    def down() -> bool:
        raise OperationalError("select 1", {}, Exception("ledger unreachable"))

    indexed(db_session, "Kindergeld Antrag")
    embedder = BudgetedQueryEmbedder(FakeQueryEmbedder({"kindergeld": query_vector()}), down)

    with serve_with(monkeypatch, db_session, embedder) as client:
        response = client.get(URL, params={"q": "kindergeld"})

    assert (response.status_code, response.json()["search_mode"]) == (200, "keyword")
