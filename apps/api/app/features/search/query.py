"""Query normalisation: the one place a raw search string becomes the text retrieval and embedding read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.features.search.text import normalise, truncate
from app.shared.list_query import SEARCH_MAX_LENGTH

_TURKIC_LOWER: Final = str.maketrans({"I": "ı", "İ": "i"})
"""Dotless and dotted capital I of the Turkish alphabet; a plain ``lower()`` would map them wrongly."""
_TURKIC_LOCALES: Final = frozenset({"tr", "az"})


@dataclass(frozen=True, slots=True)
class NormalisedQuery:
    """A query in NFC, single-spaced, lower-cased for its locale and cut to the length cap."""

    text: str
    locale: str


def _lowered(text: str, locale: str) -> str:
    """Lower-case ``text`` by the rules of ``locale``."""
    if locale in _TURKIC_LOCALES:
        return text.translate(_TURKIC_LOWER).lower()
    return text.lower().replace("i\u0307", "i")


def normalise_query(raw: str, locale: str) -> NormalisedQuery | None:
    """Return the normalised ``raw`` query for ``locale``, or ``None`` when nothing is left of it."""
    text = truncate(normalise(raw), SEARCH_MAX_LENGTH)
    return NormalisedQuery(normalise(_lowered(text, locale)), locale) if text else None
