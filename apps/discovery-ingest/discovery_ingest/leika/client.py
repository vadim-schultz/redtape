"""LeiKa stammtext client (FIM Portal host, ``source=leika``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


class LeikaClientError(Exception):
    """LeiKa stammtext could not be loaded or parsed."""


class LeikaStammtextClient:
    """Fetch LeiKa stammtext JSON from FIM Portal or a local fixture."""

    def __init__(self, base_url: str, *, stammtext: dict[str, Any] | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._fixture = stammtext

    @classmethod
    def from_json_file(cls, path: Path, *, base_url: str = "https://fimportal.de") -> LeikaStammtextClient:
        """Load a single stammtext object from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise LeikaClientError("stammtext fixture must be a JSON object")
        return cls(base_url, stammtext=data)

    def fetch_stammtext(self, redaktion_id: str, leistung_id: str) -> dict[str, Any]:
        """Return stammtext JSON for LeiKa path segments."""
        if self._fixture is not None:
            if self._fixture.get("redaktion_id") != redaktion_id or self._fixture.get("leistung_id") != leistung_id:
                raise LeikaClientError("fixture segments do not match requested ids")
            return self._fixture
        url = f"{self._base_url}/api/v1/leistung-stammtexte/{redaktion_id}/{leistung_id}/leika"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url)
        if response.status_code >= 400:
            raise LeikaClientError(f"LeiKa stammtext {response.status_code}: {response.text}")
        body = response.json()
        if not isinstance(body, dict):
            raise LeikaClientError("stammtext response must be a JSON object")
        return body
