"""The neuron meter under threads: reservations never pass the run cap, and settles keep the total whole (chapter 5, loop A)."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import cast

from discovery_ingest.budget import BudgetGuard, Reserved
from discovery_ingest.client.budget_api import BudgetAPI
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
Answer = Reservation | Denied | LedgerUnavailable


class SlowGuard(BudgetGuard):
    """A ledger stand-in whose reserve takes a few milliseconds, so threads that are not locked interleave."""

    def __init__(self) -> None:
        """Start a ledger that grants every reservation."""
        super().__init__(cast(BudgetAPI, object()))

    def reserve(self, resource: str, amount: float) -> Reserved:  # type: ignore[override]
        """Grant ``amount`` after a short pause, as a real ledger call would take."""
        time.sleep(0.005)
        return Reserved(granted=True, remaining=None)

    def adjust(self, resource: str, delta: float) -> bool:  # type: ignore[override]
        """Accept the correction."""
        return True


def _race(meter: NeuronMeter, neurons: int, threads: int) -> list[Answer]:
    """Start ``threads`` reservations at the same moment and return every answer."""
    barrier = threading.Barrier(threads)

    def attempt(_index: int) -> Answer:
        barrier.wait()
        return meter.reserve_neurons(MODEL, neurons)

    with ThreadPoolExecutor(max_workers=threads) as pool:
        return list(pool.map(attempt, range(threads)))


def test_concurrent_reservations_never_exceed_the_cap() -> None:
    """neuron meter · negative: 20 threads reserve 10 neurons each under a run cap of 100; exactly 10 are granted and 100 is used."""
    meter = NeuronMeter(SlowGuard(), 100.0)

    answers = _race(meter, 10, 20)

    granted = [answer for answer in answers if isinstance(answer, Reservation)]
    denied = [answer for answer in answers if isinstance(answer, Denied)]
    assert len(granted) == 10
    assert len(denied) == 10 and {answer.reason for answer in denied} == {"run_budget"}
    assert meter.used_neurons == 100.0


def test_concurrent_reservations_within_the_cap_are_granted_and_settle_back_to_the_actual_cost() -> None:
    """neuron meter · happy: 20 threads reserve 2 neurons each under a cap of 100; all are granted, and settling each to 1 leaves 20 used."""
    meter = NeuronMeter(SlowGuard(), 100.0)
    answers = _race(meter, 2, 20)
    reservations = [answer for answer in answers if isinstance(answer, Reservation)]
    assert len(reservations) == 20

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda reservation: meter.settle_neurons(reservation, 1.0), reservations))

    assert meter.used_neurons == 20.0
