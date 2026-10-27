"""The throttle keeps the free plan's one request per ten seconds (chapter 15, Loop A)."""

from __future__ import annotations

from discovery_ingest.browser.throttle import Throttle


class _Clock:
    def __init__(self) -> None:
        self.now = 50.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_two_calls_are_at_least_the_minimum_interval_apart() -> None:
    """throttle · the second call sleeps for the rest of the interval."""
    clock = _Clock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)

    throttle.wait()
    clock.now += 4.0
    throttle.wait()

    assert clock.sleeps == [7.0]


def test_the_first_call_and_a_call_after_the_interval_do_not_sleep() -> None:
    """throttle · no sleep for the first call or after the interval has passed."""
    clock = _Clock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)

    throttle.wait()
    clock.now += 11.0
    throttle.wait()

    assert clock.sleeps == []
