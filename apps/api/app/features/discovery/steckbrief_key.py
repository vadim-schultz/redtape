"""Resolve the FIM steckbrief key (Leistungsschluessel) from a catalogue ``raw_payload``.

Keep in lockstep with ``discovery_ingest.fim.keys``; both run the shared case table in
``tests/fixtures/steckbrief_key_cases.json``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

STECKBRIEF_KEY_PATTERN = re.compile(r"[0-9]{14}")
SCALAR_KEY_FIELDS = ("fim_id", "leistungsschluessel", "leika_key")
LIST_KEY_FIELD = "leikakeys"


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
