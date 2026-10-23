"""Shared fixtures: tests never touch real DNS."""

from __future__ import annotations

import pytest
from discovery_ingest.worker.addresses import SystemResolver

PUBLIC_TEST_ADDRESS = "93.184.216.34"


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve every host to a public address so fetcher tests need no network."""
    monkeypatch.setattr(SystemResolver, "resolve", lambda _self, _host: [PUBLIC_TEST_ADDRESS])
