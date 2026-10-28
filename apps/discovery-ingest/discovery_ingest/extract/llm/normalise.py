"""Text rules shared by grounding and mapping: quote normalisation and the document name slug."""

from __future__ import annotations

import re
import unicodedata

_LINK_TARGET = re.compile(r"\(\s*https?://[^)\s]*\s*\)")
_LIST_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_MARKERS = str.maketrans("", "", "*_`#>[]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
MAX_SLUG_LENGTH = 200


def normalise(text: str) -> str:
    """Return ``text`` lower-cased with markdown markers, list bullets and link targets removed and whitespace collapsed."""
    plain = _LINK_TARGET.sub(" ", unicodedata.normalize("NFKC", text))
    unmarked = _LIST_BULLET.sub("", plain).translate(_MARKERS).replace("|", " ")
    return " ".join(unmarked.casefold().split())


def name_slug(name: str) -> str:
    """Return the promotion slug of a German name (ASCII fold, lower case, ``-`` runs), or ``""`` when nothing is left.

    Mirrors the API's ``slugify(pick_title({"de": name}))``, which is how candidates are keyed.
    """
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM.sub("-", folded).strip("-")[:MAX_SLUG_LENGTH].strip("-")
