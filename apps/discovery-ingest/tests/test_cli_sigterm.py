"""SIGTERM closes the open run as failed: the signal raises in the drain and the run finaliser runs (chapter 2 of the pipeline suite)."""

from __future__ import annotations

import importlib
import signal
import threading
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.worker import run as run_module
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded_drain
from pydantic import SecretStr

from drain_deps_for import deps_for
from run_stub import run_response

run_cli = importlib.import_module("discovery_ingest.cli.main")

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


@pytest.fixture(autouse=True)
def _restore_sigterm() -> Iterator[None]:
    """Each test starts and ends with the process's own SIGTERM handler, whatever the test installs."""
    previous = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, previous)


def _client(monkeypatch: pytest.MonkeyPatch, finishes: list[dict[str, Any]]) -> DiscoveryIngestClient:
    transport = httpx.MockTransport(lambda request: run_response(request, finishes) or httpx.Response(404))

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))


def test_a_sigterm_raises_keyboard_interrupt_in_the_running_code() -> None:
    """sigterm · with the CLI handler installed, a SIGTERM raises KeyboardInterrupt where the process is."""
    run_cli.install_sigterm_handler()

    with pytest.raises(KeyboardInterrupt):
        signal.raise_signal(signal.SIGTERM)


def test_sigterm_during_a_drain_closes_the_run_as_failed_with_its_stop_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """sigterm · the signal raises in the drain; the run row ends failed, with stop_reason error and the interruption."""
    finishes: list[dict[str, Any]] = []
    client = _client(monkeypatch, finishes)
    run_cli.install_sigterm_handler()

    def drain(*_args: Any, **_kwargs: Any) -> Any:
        signal.raise_signal(signal.SIGTERM)

    monkeypatch.setattr(run_module, "run_worker_drain", drain)

    with pytest.raises(KeyboardInterrupt):
        run_recorded_drain(deps_for(client, PoliteUrlFetcher()), DrainPolicy())

    assert len(finishes) == 1
    assert finishes[0]["status"] == "failed"
    assert finishes[0]["stop_reason"] == "error"
    assert finishes[0]["error_detail"] == "interrupted"


def test_the_cli_restores_the_previous_sigterm_handler_when_the_command_ends() -> None:
    """sigterm · main installs its handler only for the command; the process's handler is back when main returns."""
    before = signal.getsignal(signal.SIGTERM)

    run_cli.main(["--help"])

    assert signal.getsignal(signal.SIGTERM) is before


def test_the_cli_handler_is_only_installed_in_the_main_thread() -> None:
    """sigterm · a call from another thread cannot install a signal handler, so the install is skipped rather than failing."""
    outcome: list[object] = []

    def call() -> None:
        outcome.append(run_cli.install_sigterm_handler())

    worker = threading.Thread(target=call)
    worker.start()
    worker.join()

    assert outcome == [None]
