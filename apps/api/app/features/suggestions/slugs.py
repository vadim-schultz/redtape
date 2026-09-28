"""Slug derivation for suggested documents (D5)."""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
MAX_SLUG_LENGTH = 200


def pick_title(title_i18n: dict[str, str]) -> str:
    """Resolve a slug source title: `en`, then `de`, then the first non-blank value."""
    for locale in ("en", "de"):
        value = title_i18n.get(locale, "").strip()
        if value:
            return value
    for key in sorted(title_i18n):
        value = title_i18n[key].strip()
        if value:
            return value
    return ""


def slugify(text: str) -> str:
    """NFKD-fold to ASCII, lower-case, and collapse non-alphanumerics to `-`."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_ALNUM_RE.sub("-", folded).strip("-")[:MAX_SLUG_LENGTH].strip("-")
    if not slug:
        raise ValueError(f"no usable characters to slugify in {text!r}")
    return slug
