"""FIM steckbrief keys: format, resolution from a catalogue ``raw_payload``, and URL.

``steckbrief_key`` mirrors ``app.features.discovery.steckbrief_key`` in the API; both run the case
table in ``apps/api/tests/fixtures/steckbrief_key_cases.json``, so change them together.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

STECKBRIEF_KEY_PATTERN = re.compile(r"[0-9]{14}")
STECKBRIEF_PATH = "/api/v1/leistung-steckbriefe"
SCALAR_KEY_FIELDS = ("fim_id", "leistungsschluessel", "leika_key")
LIST_KEY_FIELD = "leikakeys"


def steckbrief_url(base_url: str, key: str) -> str:
    """Return the steckbrief URL of ``key`` on the FIM Portal at ``base_url``."""
    return f"{base_url.rstrip('/')}{STECKBRIEF_PATH}/{key}"


def _candidates(raw_payload: Mapping[str, object]) -> Iterator[object]:
    for field in SCALAR_KEY_FIELDS:
        yield raw_payload.get(field)
    keys = raw_payload.get(LIST_KEY_FIELD)
    if isinstance(keys, list) and keys:
        yield keys[0]


def _valid_key(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip()
    return key if STECKBRIEF_KEY_PATTERN.fullmatch(key) else None


def steckbrief_key(raw_payload: Mapping[str, object]) -> str | None:
    """Return the first well-formed key from ``fim_id``, ``leistungsschluessel``, ``leika_key``, ``leikakeys[0]``."""
    keys = (_valid_key(candidate) for candidate in _candidates(raw_payload))
    return next((key for key in keys if key is not None), None)
