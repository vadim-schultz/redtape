"""FIM steckbrief key format and URL, shared by the probe, the enrich helpers and the client."""

from __future__ import annotations

import re

STECKBRIEF_KEY_PATTERN = re.compile(r"[0-9]{14}")
STECKBRIEF_PATH = "/api/v1/leistung-steckbriefe"


def steckbrief_url(base_url: str, key: str) -> str:
    """Return the steckbrief URL of ``key`` on the FIM Portal at ``base_url``."""
    return f"{base_url.rstrip('/')}{STECKBRIEF_PATH}/{key}"
