"""The throttle keeps the free plan's one request per ten seconds, counted from the end of the last call (chapter 15)."""

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
    """throttle · the second call starts the full interval after the first one ended."""
    clock = _Clock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)

    with throttle:
        clock.now += 6.0
    clock.now += 4.0
    with throttle:
        pass

    assert clock.sleeps == [7.0]


def test_the_first_call_and_a_call_after_the_interval_do_not_sleep() -> None:
    """throttle · no sleep for the first call or after the interval has passed."""
    clock = _Clock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)

    with throttle:
        pass
    clock.now += 11.0
    with throttle:
        pass

    assert clock.sleeps == []


def test_a_call_that_raises_still_starts_the_interval() -> None:
    """throttle · an error inside the slot does not let the next call skip the wait."""
    clock = _Clock()
    throttle = Throttle(11.0, clock=clock, sleep=clock.sleep)

    try:
        with throttle:
            raise RuntimeError("call failed")
    except RuntimeError:
        pass
    with throttle:
        pass

    assert clock.sleeps == [11.0]
