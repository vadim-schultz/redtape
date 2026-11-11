"""The query embedder stack: Workers AI client, cache, neuron budget and the unavailable stand-in (chapter 8)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import nullcontext
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from app.config import Settings
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.cloudflare_embedder import CloudflareQueryEmbedder
from app.features.search.embedder_breaker import CircuitBreakerQueryEmbedder
from app.features.search.embedder_budget import BudgetedQueryEmbedder, LedgerReservation
from app.features.search.embedder_cache import CachedQueryEmbedder
from app.features.search.embedder_factory import build_query_embedder
from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QUERY_TASK, UnavailableQueryEmbedder
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from query_embedder_support import ACCOUNT, TOKEN, FakeQueryEmbedder, ScriptedWorkersAi, answer

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
QUERY = NormalisedQuery("kindergeld", "de")
MODEL = "@cf/qwen/qwen3-embedding-0.6b"


def cloudflare(script: ScriptedWorkersAi, *, dim: int = 3) -> CloudflareQueryEmbedder:
    return CloudflareQueryEmbedder(ACCOUNT, TOKEN, MODEL, dim=dim, timeout_s=1.0, http=script.client())


def test_cloudflare_embedder_sends_the_instruction_prefix_and_returns_the_vector() -> None:
    script = ScriptedWorkersAi(lambda _request: answer([0.1, 0.2, 0.3]))

    vector = cloudflare(script).embed(QUERY)

    assert vector == (0.1, 0.2, 0.3)
    assert script.sent_text() == f"Instruct: {QUERY_TASK}\nQuery: kindergeld"
    request = script.requests[0]
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.url.path == f"/client/v4/accounts/{ACCOUNT}/ai/run/{MODEL}"


def raising(error: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def respond(_request: httpx.Request) -> httpx.Response:
        raise error

    return respond


@pytest.mark.parametrize(
    "respond",
    [
        raising(httpx.ReadTimeout("timed out")),
        raising(httpx.ConnectError("refused")),
        lambda _request: httpx.Response(500, text="boom"),
        lambda _request: httpx.Response(429, json={"success": False, "errors": [{"code": 4006}]}),
        lambda _request: httpx.Response(200, json={"success": False, "result": None}),
        lambda _request: httpx.Response(200, text="not json"),
        lambda _request: answer([0.1, 0.2]),
        lambda _request: answer([]),
    ],
    ids=["timeout", "connect", "http-500", "quota-429", "success-false", "not-json", "wrong-dim", "empty"],
)
def test_cloudflare_embedder_returns_none_on_every_failure(respond: Callable[[httpx.Request], httpx.Response]) -> None:
    assert cloudflare(ScriptedWorkersAi(respond)).embed(QUERY) is None


def test_failures_never_log_the_token_or_the_account_id(caplog: pytest.LogCaptureFixture) -> None:
    error = httpx.ConnectError(f"cannot reach {ACCOUNT} with {TOKEN}")
    caplog.set_level(logging.DEBUG)

    cloudflare(ScriptedWorkersAi(raising(error))).embed(QUERY)

    assert caplog.records
    assert TOKEN not in caplog.text
    assert ACCOUNT not in caplog.text


def test_cache_embeds_a_repeated_query_once() -> None:
    inner = FakeQueryEmbedder({"kindergeld": (1.0, 0.0, 0.0)})
    cached = CachedQueryEmbedder(inner, MODEL, size=4)

    first, second = cached.embed(QUERY), cached.embed(QUERY)

    assert first == second == (1.0, 0.0, 0.0)
    assert inner.calls == ["kindergeld"]


def test_cache_does_not_remember_a_failure() -> None:
    inner = FakeQueryEmbedder()
    cached = CachedQueryEmbedder(inner, MODEL, size=4)

    assert cached.embed(QUERY) is None
    assert cached.embed(QUERY) is None
    assert inner.calls == ["kindergeld", "kindergeld"]


def test_cache_evicts_the_least_recently_used_entry_and_size_zero_disables_it() -> None:
    inner = FakeQueryEmbedder({text: (1.0,) for text in ("a", "b", "c")})
    cached = CachedQueryEmbedder(inner, MODEL, size=2)
    for text in ("a", "b", "a", "c", "a", "b"):
        cached.embed(NormalisedQuery(text, "de"))
    assert inner.calls == ["a", "b", "c", "b"]

    uncached = CachedQueryEmbedder(inner, MODEL, size=0)
    uncached.embed(QUERY)
    uncached.embed(QUERY)
    assert inner.calls[-2:] == ["kindergeld", "kindergeld"]


def test_a_granted_reservation_lets_the_embedding_through() -> None:
    inner = FakeQueryEmbedder({"kindergeld": (1.0,)})

    assert BudgetedQueryEmbedder(inner, lambda: True).embed(QUERY) == (1.0,)


def test_a_denied_reservation_skips_the_provider_and_returns_none() -> None:
    inner = FakeQueryEmbedder({"kindergeld": (1.0,)})

    assert BudgetedQueryEmbedder(inner, lambda: False).embed(QUERY) is None
    assert inner.calls == []


def test_a_cache_hit_reserves_nothing() -> None:
    reservations: list[bool] = []
    inner = FakeQueryEmbedder({"kindergeld": (1.0,)})
    budgeted = BudgetedQueryEmbedder(inner, lambda: reservations.append(True) or True)
    cached = CachedQueryEmbedder(budgeted, MODEL, size=4)

    cached.embed(QUERY)
    cached.embed(QUERY)

    assert len(reservations) == 1


def ledger_reservation(session: Session) -> LedgerReservation:
    return LedgerReservation(lambda: nullcontext(session), Decimal("0.10"), clock=lambda: NOW)


def used_neurons(session: Session) -> Decimal:
    return BudgetService(DiscoveryRepository(session)).status(BudgetResource.NEURONS, NOW).used


def test_the_ledger_reservation_is_granted_and_recorded_against_the_neuron_ledger(db_session: Session) -> None:
    before = used_neurons(db_session)

    assert ledger_reservation(db_session)() is True
    assert used_neurons(db_session) == before + Decimal("0.10")


def test_the_ledger_reservation_is_denied_once_the_day_is_exhausted(db_session: Session) -> None:
    BudgetService(DiscoveryRepository(db_session)).exhaust(BudgetResource.NEURONS, NOW)
    before = used_neurons(db_session)

    assert ledger_reservation(db_session)() is False
    assert used_neurons(db_session) == before


def test_a_ledger_failure_degrades_to_none_instead_of_raising() -> None:
    def broken() -> bool:
        raise SQLAlchemyError("ledger down")

    inner = FakeQueryEmbedder({"kindergeld": (1.0,)})

    assert BudgetedQueryEmbedder(inner, broken).embed(QUERY) is None
    assert inner.calls == []


def settings_with(token: str, account: str) -> Settings:
    return Settings(cloudflare_ai_api_token=token, cloudflare_account_id=account)


def test_the_factory_builds_the_real_stack_when_credentials_are_set() -> None:
    embedder = build_query_embedder(
        settings_with(TOKEN, ACCOUNT), lambda: True, http=ScriptedWorkersAi(lambda _r: answer([0.0])).client()
    )

    assert isinstance(embedder, CachedQueryEmbedder)


@pytest.mark.parametrize(("token", "account"), [("", ACCOUNT), (TOKEN, ""), ("", "")])
def test_the_factory_returns_the_unavailable_embedder_without_credentials(token: str, account: str) -> None:
    embedder = build_query_embedder(settings_with(token, account), lambda: True)

    assert isinstance(embedder, UnavailableQueryEmbedder)
    assert embedder.embed(QUERY) is None


class Clock:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def breaker(inner: FakeQueryEmbedder, clock: Clock) -> CircuitBreakerQueryEmbedder:
    return CircuitBreakerQueryEmbedder(inner, failures=3, cooldown_s=30.0, clock=clock)


def test_a_failing_provider_is_skipped_after_the_failure_threshold_until_the_cooldown_ends() -> None:
    clock, inner = Clock(), FakeQueryEmbedder()
    guarded = breaker(inner, clock)

    results = [guarded.embed(QUERY) for _ in range(6)]

    assert results == [None] * 6
    assert len(inner.calls) == 3


def test_one_probe_goes_through_after_the_cooldown_and_a_success_closes_the_breaker() -> None:
    clock, inner = Clock(), FakeQueryEmbedder()
    guarded = breaker(inner, clock)
    for _ in range(3):
        guarded.embed(QUERY)
    clock.now += 31
    inner.vectors = {"kindergeld": (1.0,)}

    assert guarded.embed(QUERY) == (1.0,)
    assert guarded.embed(QUERY) == (1.0,)
    assert len(inner.calls) == 5


def test_a_failed_probe_keeps_the_breaker_open_for_another_cooldown() -> None:
    clock, inner = Clock(), FakeQueryEmbedder()
    guarded = breaker(inner, clock)
    for _ in range(3):
        guarded.embed(QUERY)
    clock.now += 31
    guarded.embed(QUERY)
    guarded.embed(QUERY)

    assert len(inner.calls) == 4
    clock.now += 31
    guarded.embed(QUERY)
    assert len(inner.calls) == 5


def test_a_success_resets_the_failure_count() -> None:
    clock, inner = Clock(), FakeQueryEmbedder()
    guarded = breaker(inner, clock)
    guarded.embed(QUERY)
    guarded.embed(QUERY)
    inner.vectors = {"kindergeld": (1.0,)}
    guarded.embed(QUERY)
    inner.vectors = {}
    guarded.embed(QUERY)
    guarded.embed(QUERY)

    assert len(inner.calls) == 5


def test_an_open_breaker_reserves_no_neurons() -> None:
    reservations: list[bool] = []
    clock = Clock()
    inner = FakeQueryEmbedder()
    budgeted = BudgetedQueryEmbedder(inner, lambda: reservations.append(True) or True)
    guarded = CircuitBreakerQueryEmbedder(budgeted, failures=2, cooldown_s=30.0, clock=clock)

    for _ in range(5):
        guarded.embed(QUERY)

    assert len(reservations) == 2
