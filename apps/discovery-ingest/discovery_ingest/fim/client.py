"""FIM Portal steckbrief client for discovery enrich."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


class FimClientError(Exception):
    """FIM response could not be loaded or parsed."""


class FimSteckbriefClient:
    """Fetch steckbrief JSON from FIM Portal or a local fixture."""

    def __init__(self, base_url: str, *, steckbrief: dict[str, Any] | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._fixture = steckbrief

    @classmethod
    def from_json_file(cls, path: Path, *, base_url: str = "https://fimportal.de") -> FimSteckbriefClient:
        """Load a single steckbrief object from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FimClientError("steckbrief fixture must be a JSON object")
        return cls(base_url, steckbrief=data)

    def fetch_steckbrief(self, leistungsschluessel: str) -> dict[str, Any]:
        """Return steckbrief JSON for ``leistungsschluessel``."""
        if self._fixture is not None:
            key = self._fixture.get("leistungsschluessel")
            if key != leistungsschluessel:
                raise FimClientError(f"fixture key {key!r} does not match {leistungsschluessel!r}")
            return self._fixture
        url = f"{self._base_url}/api/v1/leistung-steckbriefe/{leistungsschluessel}"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url)
        if response.status_code >= 400:
            raise FimClientError(f"FIM steckbrief {response.status_code}: {response.text}")
        body = response.json()
        if not isinstance(body, dict):
            raise FimClientError("steckbrief response must be a JSON object")
        return body
