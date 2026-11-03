"""Errors the machine API raises, carrying a bounded body with the API key scrubbed."""

from __future__ import annotations

import httpx

HTTP_INSUFFICIENT_STORAGE = 507
DATABASE_LIMIT_DETAIL = "database_soft_limit"
MAX_ERROR_DETAIL_CHARS = 1000
"""Same bound ``worker/run.py`` applies to ``error_detail``."""
TRUNCATION_MARK = "...[truncated]"
REDACTED = "<redacted>"


class DiscoveryMachineApiError(Exception):
    """Machine API returned a non-success status."""

    def __init__(self, status_code: int, detail: str) -> None:
        """Keep the status and the body text that explains it."""
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"discovery machine API {status_code}: {detail}")

    @property
    def is_database_limit(self) -> bool:
        """Whether the API refused a write because the database is above its soft limit (stop, do not fail)."""
        return self.status_code == HTTP_INSUFFICIENT_STORAGE and DATABASE_LIMIT_DETAIL in self.detail

    @classmethod
    def from_response(cls, response: httpx.Response, secret: str) -> DiscoveryMachineApiError:
        """Build the error for a failed ``response``, replacing ``secret`` in its body and bounding the length."""
        return cls(response.status_code, _bounded(response.text, secret))


def _bounded(text: str, secret: str) -> str:
    """Return ``text`` with ``secret`` redacted, cut to ``MAX_ERROR_DETAIL_CHARS`` plus a truncation mark."""
    if secret:
        text = text.replace(secret, REDACTED)
    if len(text) <= MAX_ERROR_DETAIL_CHARS:
        return text
    return text[:MAX_ERROR_DETAIL_CHARS] + TRUNCATION_MARK
