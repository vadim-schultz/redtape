"""Lifespan locale load: a logged fallback on failure, and a TTL refresh that heals."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import pytest
from app import lifespan as lifespan_module
from app.lifespan import app_lifespan
from app.middleware.locale import LocaleResolverMiddleware
from litestar import Litestar, Request, get
from litestar.middleware.base import DefineMiddleware
from litestar.testing import TestClient


def _scripted_loader(
    outcomes: list[set[str] | Exception],
) -> tuple[Callable[[], set[str]], Callable[[], int]]:
    """Return a fake loader replaying `outcomes` in order (repeating the last), plus a call counter."""
    calls = 0

    def loader() -> set[str]:
        nonlocal calls
        outcome = outcomes[min(calls, len(outcomes) - 1)]
        calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return loader, lambda: calls


def _patch_loader(monkeypatch: pytest.MonkeyPatch, outcomes: list[set[str] | Exception]) -> Callable[[], int]:
    loader, call_count = _scripted_loader(outcomes)
    monkeypatch.setattr(lifespan_module, "_load_enabled_locales", loader)
    return call_count


@pytest.fixture(autouse=True)
def _fast_intervals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifespan_module, "REFRESH_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(lifespan_module, "RETRY_INTERVAL_SECONDS", 0.01)


@get("/echo-locale", sync_to_thread=False)
def _echo_locale(request: Request) -> dict[str, str]:
    return {"locale": request.state["locale"]}


def _app() -> Litestar:
    # `logging_config=None` keeps Litestar from calling `dictConfig` on construction,
    # which would otherwise strip pytest's `caplog` handler from the root logger.
    return Litestar(
        route_handlers=[_echo_locale],
        middleware=[DefineMiddleware(LocaleResolverMiddleware)],
        lifespan=[app_lifespan],
        logging_config=None,
    )


def _eventually(predicate: Callable[[], bool], timeout: float = 2.0) -> None:
    """Poll `predicate` until it is true, or fail at `timeout`; no fixed sleeps in assertions."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate(), "condition was never satisfied within the timeout"


# --- characterisation (green now) -------------------------------------------------


def test_startup_loads_the_enabled_codes_into_app_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_loader(monkeypatch, [{"de", "fr"}])

    with TestClient(_app()) as client:
        assert client.app.state.enabled_locale_codes == {"de", "fr"}


def test_a_request_with_an_enabled_accept_language_resolves_it(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_loader(monkeypatch, [{"de", "fr"}])

    with TestClient(_app()) as client:
        response = client.get("/echo-locale", headers={"Accept-Language": "fr"})

    assert response.json() == {"locale": "fr"}


# --- red: silent fallback and never refreshing (the defect, C6) -------------------


def test_a_startup_failure_is_logged_with_the_error_and_the_app_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_loader(monkeypatch, [RuntimeError("db down")])

    with caplog.at_level(logging.ERROR, logger="app.lifespan"), TestClient(_app()) as client:
        assert client.app.state.enabled_locale_codes == {"de", "en"}

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert error_records, "expected an ERROR record for the startup failure"
    assert "db down" in error_records[0].getMessage()
    assert error_records[0].exc_info is not None


def test_an_empty_locale_table_is_logged_and_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_loader(monkeypatch, [set()])

    with caplog.at_level(logging.WARNING, logger="app.lifespan"), TestClient(_app()) as client:
        assert client.app.state.enabled_locale_codes == {"de", "en"}

    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_the_fallback_ends_when_the_database_answers(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_loader(monkeypatch, [RuntimeError("db down"), {"de", "en", "fr"}])

    with caplog.at_level(logging.INFO, logger="app.lifespan"), TestClient(_app()) as client:
        _eventually(lambda: client.app.state.enabled_locale_codes == {"de", "en", "fr"})

    assert any(r.levelno == logging.INFO and "fallback" in r.getMessage().lower() for r in caplog.records)


def test_a_locale_enabled_after_startup_is_served_within_the_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    # The second outcome blocks until the test releases it, so the first request is
    # deterministically checked before the refresh that enables "fr" lands.
    release_second_outcome = threading.Event()
    calls = 0

    def loader() -> set[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"de", "en"}
        release_second_outcome.wait(timeout=2.0)
        return {"de", "en", "fr"}

    monkeypatch.setattr(lifespan_module, "_load_enabled_locales", loader)

    with TestClient(_app()) as client:
        first = client.get("/echo-locale", headers={"Accept-Language": "fr"})
        assert first.json() == {"locale": "de"}

        release_second_outcome.set()
        _eventually(lambda: client.get("/echo-locale", headers={"Accept-Language": "fr"}).json() == {"locale": "fr"})


def test_a_failed_refresh_keeps_the_last_good_set_and_logs_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    call_count = _patch_loader(monkeypatch, [{"de", "fr"}, RuntimeError("blip"), RuntimeError("blip")])

    with caplog.at_level(logging.WARNING, logger="app.lifespan"), TestClient(_app()) as client:
        _eventually(lambda: call_count() >= 3)
        assert client.app.state.enabled_locale_codes == {"de", "fr"}

    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_a_refresh_that_finds_no_enabled_locale_keeps_the_last_good_set(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = _patch_loader(monkeypatch, [{"de", "fr"}, set()])

    with TestClient(_app()) as client:
        _eventually(lambda: call_count() >= 2)
        assert client.app.state.enabled_locale_codes == {"de", "fr"}


def test_a_steady_refresh_does_not_log_above_debug(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    call_count = _patch_loader(monkeypatch, [{"de", "fr"}])

    with caplog.at_level(logging.DEBUG, logger="app.lifespan"), TestClient(_app()):
        _eventually(lambda: call_count() >= 4)

    info_or_above = [r for r in caplog.records if r.levelno >= logging.INFO]
    assert len(info_or_above) <= 1


def test_shutdown_stops_the_refresh_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = _patch_loader(monkeypatch, [{"de", "en"}])

    with TestClient(_app()):
        _eventually(lambda: call_count() >= 1)

    count_at_shutdown = call_count()
    time.sleep(0.2)
    assert call_count() == count_at_shutdown
