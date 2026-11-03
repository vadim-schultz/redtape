"""FIM Portal steckbrief client for discovery enrich."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from pydantic import JsonValue

from discovery_ingest.fim.keys import steckbrief_url
from discovery_ingest.fim.models import Steckbrief


class FimClientError(Exception):
    """FIM response could not be loaded or parsed."""


class FimSteckbriefClient:
    """Fetch steckbrief JSON from FIM Portal or a local fixture."""

    def __init__(self, base_url: str, *, steckbrief: Steckbrief | None = None) -> None:
        """Keep the base URL and the optional fixture that replaces the live fetch."""
        self._base_url = base_url.rstrip("/")
        self._fixture = steckbrief

    @classmethod
    def from_json_file(cls, path: Path, *, base_url: str = "https://fimportal.de") -> FimSteckbriefClient:
        """Load a single steckbrief object from a JSON file and validate it at load time."""
        data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FimClientError("steckbrief fixture must be a JSON object")
        try:
            steckbrief = Steckbrief.from_object(data)
        except ValueError as err:
            raise FimClientError(str(err)) from err
        return cls(base_url, steckbrief=steckbrief)

    def fetch_steckbrief(self, leistungsschluessel: str) -> Steckbrief:
        """Return the steckbrief for ``leistungsschluessel``."""
        if self._fixture is not None:
            key = self._fixture.leistungsschluessel
            if key != leistungsschluessel:
                raise FimClientError(f"fixture key {key!r} does not match {leistungsschluessel!r}")
            return self._fixture
        url = steckbrief_url(self._base_url, leistungsschluessel)
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url)
        if response.status_code >= 400:
            raise FimClientError(f"FIM steckbrief {response.status_code}: {response.text}")
        body: JsonValue = response.json()
        if not isinstance(body, dict):
            raise FimClientError("steckbrief response must be a JSON object")
        try:
            return Steckbrief.from_object(body)
        except ValueError as err:
            raise FimClientError(str(err)) from err
