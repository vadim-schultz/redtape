"""LeiKa stammtext sources (FIM Portal host, ``source=leika``): a local fixture or the live portal."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import JsonValue

from discovery_ingest.fim.models import Stammtext


class LeikaClientError(Exception):
    """LeiKa stammtext could not be loaded or parsed."""


class StammtextSource(Protocol):
    """Anything that returns the stammtext for a LeiKa path or raises :class:`LeikaClientError`."""

    def fetch_stammtext(self, redaktion_id: str, leistung_id: str) -> Stammtext:
        """Return the stammtext for the LeiKa path segments."""
        ...


class FixtureStammtextSource:
    """Serve one stammtext loaded from a JSON fixture; only its own path segments can be asked for."""

    def __init__(self, stammtext: Stammtext) -> None:
        """Keep the fixture stammtext."""
        self._stammtext = stammtext

    @classmethod
    def from_json_file(cls, path: Path) -> FixtureStammtextSource:
        """Load a single stammtext object from a JSON file and validate it at load time."""
        data: JsonValue = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise LeikaClientError("stammtext fixture must be a JSON object")
        try:
            stammtext = Stammtext.from_object(data)
        except ValueError as err:
            raise LeikaClientError(str(err)) from err
        return cls(stammtext)

    def fetch_stammtext(self, redaktion_id: str, leistung_id: str) -> Stammtext:
        """Return the fixture when both segments match, else raise :class:`LeikaClientError`."""
        if self._stammtext.redaktion_id != redaktion_id or self._stammtext.leistung_id != leistung_id:
            raise LeikaClientError("fixture segments do not match requested ids")
        return self._stammtext


class HttpStammtextSource:
    """Fetch LeiKa stammtext JSON from the FIM Portal with a GET per path."""

    def __init__(self, base_url: str, *, http_client: httpx.Client | None = None) -> None:
        """Keep the portal base URL and an optional HTTP client; without one each fetch opens its own."""
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def fetch_stammtext(self, redaktion_id: str, leistung_id: str) -> Stammtext:
        """GET the stammtext for the path segments and validate its JSON object."""
        url = f"{self._base_url}/api/v1/leistung-stammtexte/{redaktion_id}/{leistung_id}/leika"
        response = self._get(url)
        if response.status_code >= 400:
            raise LeikaClientError(f"LeiKa stammtext {response.status_code}: {response.text}")
        body: JsonValue = response.json()
        if not isinstance(body, dict):
            raise LeikaClientError("stammtext response must be a JSON object")
        try:
            return Stammtext.from_object(body)
        except ValueError as err:
            raise LeikaClientError(str(err)) from err

    def _get(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url)
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            return client.get(url)
