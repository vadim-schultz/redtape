"""Character meter · reserve, settle and refund on the azure_translator_chars ledger, all or nothing, and a stop when denied."""

from __future__ import annotations

import threading
import time

import httpx
import pytest
from discovery_ingest.translation.character_meter import CharacterMeter
from discovery_ingest.translation.meter import UsageDenied, UsageReservation
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import Usage
from discovery_ingest.worker.stop import StopDrain

from azure_transport import engine as azure_engine
from azure_transport import faithful_answer
from ledger_fakes import CHARACTERS, FakeLedger, guard_for
from translation_fakes import batch, unit

MODEL = "azure-translator"
ONE_UNIT = batch(unit("a", "Antrag", "Gebühr"))


def _granted(answer: UsageReservation | UsageDenied) -> UsageReservation:
    assert isinstance(answer, UsageReservation), answer
    return answer


def test_reserve_grants_the_exact_characters_when_the_ledger_has_room(monkeypatch: pytest.MonkeyPatch) -> None:
    """Character meter · reserve grants the exact characters when the ledger has room."""
    ledger = FakeLedger(9000.0, characters=4000.0)
    meter = CharacterMeter(guard_for(monkeypatch, ledger))

    reservation = _granted(meter.reserve(Usage("characters", 1234.0), MODEL))

    assert reservation.usage == Usage("characters", 1234.0)
    assert ledger.characters is not None and ledger.characters.remaining == 2766.0
    assert meter.used == 1234.0


def test_settle_to_the_billed_figure_adjusts_the_ledger_by_the_difference(monkeypatch: pytest.MonkeyPatch) -> None:
    """Character meter · settle to the billed figure adjusts the ledger by the difference."""
    ledger = FakeLedger(9000.0, characters=4000.0)
    meter = CharacterMeter(guard_for(monkeypatch, ledger))
    reservation = _granted(meter.reserve(Usage("characters", 1000.0), MODEL))

    meter.settle(reservation, Usage("characters", 900.0))

    assert ledger.characters is not None and ledger.characters.remaining == 3100.0
    assert meter.used == 900.0
    assert ledger.writes_to(CHARACTERS) == ["reserve", "adjust"]


def test_refund_returns_the_reservation_of_a_call_that_billed_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Character meter · refund returns the reservation of a call that billed nothing."""
    ledger = FakeLedger(9000.0, characters=4000.0)
    meter = CharacterMeter(guard_for(monkeypatch, ledger))
    reservation = _granted(meter.reserve(Usage("characters", 500.0), MODEL))

    meter.refund(reservation)

    assert ledger.characters is not None and ledger.characters.remaining == 4000.0
    assert meter.used == 0.0


def test_a_ten_thousand_character_request_with_four_thousand_remaining_is_denied_and_reserves_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Character meter · a 10,000-character request with 4,000 remaining is denied and reserves nothing."""
    ledger = FakeLedger(9000.0, characters=4000.0)
    meter = CharacterMeter(guard_for(monkeypatch, ledger))

    answer = meter.reserve(Usage("characters", 10_000.0), MODEL)

    assert answer == UsageDenied("ledger")
    assert ledger.characters is not None and ledger.characters.remaining == 4000.0
    assert meter.used == 0.0 and ledger.writes_to(CHARACTERS) == ["reserve"]


def test_an_unreadable_ledger_is_a_denial_and_no_azure_request_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Character meter · an unreadable ledger is a denial, and no HTTP request is sent."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return faithful_answer(request)

    # The adapter's HTTP client is made before the ledger client patches httpx.Client for this test.
    adapter = azure_engine(handler)
    meter = CharacterMeter(guard_for(monkeypatch, FakeLedger(9000.0, characters=4000.0, down=True)))

    assert meter.reserve(Usage("characters", 100.0), MODEL) == UsageDenied("ledger_unavailable")
    with pytest.raises(StopDrain) as stop:
        MeteredTranslator(adapter, meter).translate(ONE_UNIT)

    assert stop.value.reason == "llm_budget" and sent == []


def test_concurrent_reserves_from_two_threads_never_exceed_the_remaining_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Character meter · concurrent reserves from two threads never exceed the remaining amount."""
    ledger = FakeLedger(9000.0, characters=10_000.0)

    def slow_ledger(request: httpx.Request) -> httpx.Response:
        time.sleep(0.02)  # the window in which two unlocked reserves would both read the same remaining amount
        return ledger(request)

    meter = CharacterMeter(guard_for(monkeypatch, slow_ledger))
    start = threading.Barrier(2)
    answers: list[UsageReservation | UsageDenied] = []

    def reserve() -> None:
        start.wait()
        answers.append(meter.reserve(Usage("characters", 6000.0), MODEL))

    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sum(isinstance(answer, UsageReservation) for answer in answers) == 1
    assert answers.count(UsageDenied("ledger")) == 1
    assert ledger.characters is not None and ledger.characters.remaining == 4000.0
    assert meter.used == 6000.0
