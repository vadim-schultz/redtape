"""Names that are data to type into a form (an address, a number), never a document someone brings."""

from __future__ import annotations

import re

DATA_FIELD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(Anschrift|Adresse|Name und)\b", re.IGNORECASE),
    re.compile(r"^[\w-]*nummer\b", re.IGNORECASE),
)


def is_data_field(name: str) -> bool:
    """Return whether ``name`` starts like an address or an identifier, such as ``Kundennummer der Person``."""
    return any(pattern.search(name) for pattern in DATA_FIELD_PATTERNS)
