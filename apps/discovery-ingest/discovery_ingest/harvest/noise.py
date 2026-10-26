"""The one place that decides whether a harvested fragment is a document name."""

from __future__ import annotations

MIN_LENGTH = 3
MAX_LENGTH = 200
SENTENCE_ENDINGS = (".", ":")
STOP_LIST = frozenset({"siehe unten", "siehe oben", "keine", "entfällt", "nicht angegeben"})


def is_noise(item: str) -> bool:
    """Return whether ``item`` is too short or long, a sentence or intro, or a stop-list phrase."""
    if not MIN_LENGTH <= len(item) <= MAX_LENGTH:
        return True
    return item.endswith(SENTENCE_ENDINGS) or item.casefold() in STOP_LIST
