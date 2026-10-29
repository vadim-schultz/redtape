"""Names that are not a specific paper or file: generic words, leaflets, authority lists, devices, apps."""

from __future__ import annotations

import re

_GENERIC_WORD = r"(?:Antrags?formular|Formular|Antrag|Anträge|Bestätigung|Bekanntmachung|Sonstige)"

GENERIC_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    # a generic word alone, with an optional PDF- or Online- prefix and a plural ending
    re.compile(rf"^(?:(?:PDF|Online)-)?{_GENERIC_WORD}(?:e|en|s|n|se)?$", re.IGNORECASE),
    # lists of authorities and data-protection notices
    re.compile(r"^(?:Behördenliste|Datenschutz|Informationen? zum Datenschutz)", re.IGNORECASE),
    # information sheets and leaflets
    re.compile(r"^(?:Merkblatt|Informationen?|Ausfüllhinweise?|Hinweise?)\b", re.IGNORECASE),
    # devices and apps (case-sensitive, so that ``Knapp`` is not an app)
    re.compile(r"(?:[Gg]er[äa]t|[Pp]hone|App\d*)$"),
    # categories of works (Filmwerke, Tonwerke) and the category Spiele
    re.compile(r"^(?:\w*werke|Spiele)$", re.IGNORECASE),
)


def is_generic_name(name: str) -> bool:
    """Return whether ``name`` is a generic word alone, an information sheet, an authority list, a device or a category."""
    stripped = name.strip()
    return any(pattern.search(stripped) for pattern in GENERIC_NAME_PATTERNS)
