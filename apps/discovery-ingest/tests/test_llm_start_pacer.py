"""The Workers AI start pacer: starts are spaced by the interval even when threads enter at the same moment (chapter 5, loop B)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from discovery_ingest.extract.llm.start_pacer import StartPacer


def test_sequential_starts_are_spaced_by_the_interval() -> None:
    """start pacer · happy: three calls one after another wait one interval before each of the second and third."""
    now = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    pacer = StartPacer(1.0, clock=lambda: now[0], sleep=sleep)
    for _call in range(3):
        with pacer:
            pass

    assert sleeps == [1.0, 1.0]


def test_concurrent_starts_at_the_same_instant_get_distinct_slots() -> None:
    """start pacer · negative: three threads enter at one instant; they wait 0, 1 and 2 intervals, never the same slot."""
    sleeps: list[float] = []
    lock = threading.Lock()

    def sleep(seconds: float) -> None:
        with lock:
            sleeps.append(seconds)

    pacer = StartPacer(1.0, clock=lambda: 0.0, sleep=sleep)
    barrier = threading.Barrier(3)

    def start(_index: int) -> None:
        barrier.wait()
        with pacer:
            pass

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(start, range(3)))

    assert sorted(sleeps) == [1.0, 2.0]
