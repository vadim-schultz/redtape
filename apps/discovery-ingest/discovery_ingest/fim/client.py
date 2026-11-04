"""FIM Portal steckbrief sources for discovery enrich: a local fixture or the live portal."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import JsonValue

from discovery_ingest.fim.keys import steckbrief_url
from discovery_ingest.fim.models import Steckbrief


class FimClientError(Exception):
    """FIM response could not be loaded or parsed."""


class SteckbriefSource(Protocol):
    """Anything that returns the steckbrief for a 14-digit key or raises :class:`FimClientError`."""

    def fetch_steckbrief(self, leistungsschluessel: str) -> Steckbrief:
        """Return the steckbrief for ``leistungsschluessel``."""
        ...


class FixtureSteckbriefSource:
    """Serve one steckbrief loaded from a JSON fixture; only its own key can be asked for."""

    def __init__(self, steckbrief: Steckbrief) -> None:
        """Keep the fixture steckbrief."""
        self._steckbrief = steckbrief

    @classmethod
    def from_json_file(cls, path: Path) -> FixtureSteckbriefSource:
        """Load a single steckbrief object from a JSON file and validate it at load time."""
        data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FimClientError("steckbrief fixture must be a JSON object")
        try:
            steckbrief = Steckbrief.from_object(data)
        except ValueError as err:
            raise FimClientError(str(err)) from err
        return cls(steckbrief)

    def fetch_steckbrief(self, leistungsschluessel: str) -> Steckbrief:
        """Return the fixture when its key is ``leistungsschluessel``, else raise :class:`FimClientError`."""
        key = self._steckbrief.leistungsschluessel
        if key != leistungsschluessel:
            raise FimClientError(f"fixture key {key!r} does not match {leistungsschluessel!r}")
        return self._steckbrief


class HttpSteckbriefSource:
    """Fetch steckbrief JSON from the FIM Portal with a GET per key."""

    def __init__(self, base_url: str, *, http_client: httpx.Client | None = None) -> None:
        """Keep the portal base URL and an optional HTTP client; without one each fetch opens its own."""
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def fetch_steckbrief(self, leistungsschluessel: str) -> Steckbrief:
        """GET the steckbrief for ``leistungsschluessel`` and validate its JSON object."""
        url = steckbrief_url(self._base_url, leistungsschluessel)
        response = self._get(url)
        if response.status_code >= 400:
            raise FimClientError(f"FIM steckbrief {response.status_code}: {response.text}")
        body: JsonValue = response.json()
        if not isinstance(body, dict):
            raise FimClientError("steckbrief response must be a JSON object")
        try:
            return Steckbrief.from_object(body)
        except ValueError as err:
            raise FimClientError(str(err)) from err

    def _get(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url)
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            return client.get(url)
