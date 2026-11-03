"""Slug derivation for suggested documents (D5)."""

from __future__ import annotations

import re
import unicodedata

from app.i18n_resolution import pick_i18n
from app.shared.locale import ResolvedLocale

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
MAX_SLUG_LENGTH = 200


def pick_title(title_i18n: dict[str, str]) -> str:
    """Resolve a slug source title: `en`, then `de`, then the first non-blank value.

    Slug source, intentionally not display order: this feeds `Document.slug` and the
    candidate dedup key, so it keeps its en-first order even though the shared picker's
    default is de-first (D3 in the audit's gaps-and-decisions).
    """
    return pick_i18n(title_i18n, ResolvedLocale(code="en", enabled=set(title_i18n)), fallback=("de",)).strip()


def slugify(text: str) -> str:
    """NFKD-fold to ASCII, lower-case, and collapse non-alphanumerics to `-`."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_ALNUM_RE.sub("-", folded).strip("-")[:MAX_SLUG_LENGTH].strip("-")
    if not slug:
        raise ValueError(f"no usable characters to slugify in {text!r}")
    return slug
