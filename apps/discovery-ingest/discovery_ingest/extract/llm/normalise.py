"""Text rules shared by grounding and mapping: quote normalisation and the document name slug."""

from __future__ import annotations

import re
import unicodedata

_LINK_TARGET = re.compile(r"\(\s*https?://[^)\s]*\s*\)")
# A list marker is a bullet glyph that follows whitespace (or starts the text) and is followed by whitespace;
# ``*`` is already gone with the markdown markers by the time this runs.
_LIST_BULLET = re.compile(r"(?<!\S)[-+•·]\s+")
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"
_QUOTE_MARKS = "\"'\u201e\u201c\u201d\u201a\u2018\u2019\u00ab\u00bb\u2039\u203a"
_MARKERS = "*_`#>[]"
# One table for both sides of a grounding match: dashes become a hyphen, table bars a space, quote marks and markdown
# markers disappear.
_FOLD = str.maketrans(_DASHES + "|", "-" * len(_DASHES) + " ", _QUOTE_MARKS + _MARKERS)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
MAX_SLUG_LENGTH = 200


def normalise(text: str) -> str:
    """Return ``text`` in the one form that quote and page text are compared in.

    Lower-cased, with link targets, markdown markers, quote marks and list bullets (anywhere after whitespace) removed,
    dashes folded to a hyphen and whitespace collapsed. Letters are never touched.
    """
    plain = _LINK_TARGET.sub(" ", unicodedata.normalize("NFKC", text)).translate(_FOLD)
    return " ".join(_LIST_BULLET.sub("", plain).casefold().split())


def name_slug(name: str) -> str:
    """Return the promotion slug of a German name (ASCII fold, lower case, ``-`` runs), or ``""`` when nothing is left.

    Mirrors the API's ``slugify(pick_title({"de": name}))``, which is how candidates are keyed.
    """
    return fold_slug(name)[:MAX_SLUG_LENGTH].strip("-")


def fold_slug(text: str) -> str:
    """Return ``text`` ASCII-folded and lower-cased with every non-alphanumeric run as one ``-``, never truncated."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM.sub("-", folded).strip("-")
