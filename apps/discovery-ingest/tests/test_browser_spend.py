"""A browser call is settled once, at the browser time it cost, including when it failed (chapter 2 of the pipeline suite)."""

from __future__ import annotations

import httpx
import pytest
from discovery_ingest.browser.budget import BrowserBudget
from discovery_ingest.browser.client import CloudflareBrowserClient
from discovery_ingest.browser.errors import BrowserRequestError
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.config import load_browser_settings
from discovery_ingest.worker.browser_spend import BrowserSpend

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "tok-SECRET-0123456789"
PAGE = "https://portal.example/service/1"


class Answer:
    """The ledger's answer to a reservation: granted with plenty left."""

    granted = True
    remaining = 1000.0


class FakeLedger:
    """A budget route that grants every reservation and keeps each write in order."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, str, float]] = []

    def reserve(self, resource: str, amount: float) -> Answer:
        """Grant the reservation and record it."""
        self.writes.append(("reserve", resource, amount))
        return Answer()

    def adjust(self, resource: str, delta: float) -> None:
        """Record the correction."""
        self.writes.append(("adjust", resource, delta))

    def exhaust(self, resource: str) -> None:
        """Record the exhaustion."""
        self.writes.append(("exhaust", resource, 0.0))


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", TOKEN)


def _spend(ledger: FakeLedger) -> BrowserSpend:
    return BrowserSpend(BrowserBudget(480.0), BudgetGuard(ledger))  # type: ignore[arg-type]


def _adjustments(ledger: FakeLedger) -> list[float]:
    return [delta for action, _, delta in ledger.writes if action == "adjust"]


def test_a_failed_browser_call_is_settled_once_at_its_measured_duration() -> None:
    """spend · a 5xx that cost 4 s reserves 30 s and adjusts once, by 4 s minus 30 s, not by the whole estimate."""
    ledger = FakeLedger()
    spend = _spend(ledger)

    def fail() -> str:
        raise BrowserRequestError("Cloudflare HTTP 503", retryable=True, ms_used=4000)

    with pytest.raises(BrowserRequestError):
        spend.call(fail, len)

    assert ledger.writes == [("reserve", "browser_seconds", 30.0), ("adjust", "browser_seconds", -26.0)]
    assert spend.used_seconds == 4.0


def test_a_call_that_never_reached_cloudflare_settles_to_zero() -> None:
    """spend · a connection refused before the send books no browser time, so the 30 s reservation comes back whole."""
    ledger = FakeLedger()
    spend = _spend(ledger)
    client = _refusing_client()

    with pytest.raises(BrowserRequestError):
        spend.call(lambda: client.render(PAGE), lambda page: page.ms_used)

    assert _adjustments(ledger) == [-30.0]
    assert spend.used_seconds == 0.0


def _refusing_client() -> CloudflareBrowserClient:
    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host", request=request)

    return CloudflareBrowserClient(
        load_browser_settings(),
        user_agent="RedtapeBot/1.0",
        http=httpx.Client(transport=httpx.MockTransport(refused)),
        throttle=Throttle(0.0),
    )


def test_a_call_that_raised_without_a_reported_cost_settles_at_its_wall_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """spend · an error with no ms_used (a non-Cloudflare failure) settles at the measured wall time, never at 30 s."""
    ledger = FakeLedger()
    spend = _spend(ledger)
    ticks = iter([10.0, 14.5])
    monkeypatch.setattr("discovery_ingest.worker.browser_spend.monotonic", lambda: next(ticks))

    def fail() -> str:
        raise BrowserRequestError("timed out inside the adapter", retryable=True)

    with pytest.raises(BrowserRequestError):
        spend.call(fail, len)

    assert _adjustments(ledger) == [pytest.approx(4.5 - 30.0)]
    assert spend.used_seconds == pytest.approx(4.5)


def test_a_successful_call_still_settles_once_at_the_reported_cost() -> None:
    """spend · the success path is unchanged: 6 s reported, 24 s given back, one adjustment."""
    ledger = FakeLedger()
    spend = _spend(ledger)
    assert spend.call(lambda: 6000, lambda ms: ms) == 6000

    assert _adjustments(ledger) == [-24.0]
    assert spend.used_seconds == 6.0
