"""Document facts of the page cleaner: the primary language subtag and the title."""

from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

_SUBTAG_SEPARATOR = re.compile(r"[-_]")


def page_language(tree: LexborHTMLParser) -> str | None:
    """Return the primary subtag of ``<html lang>`` in lower case, or ``None`` when it is absent or empty."""
    root = tree.css_first("html")
    declared = (root.attributes.get("lang") if root is not None else None) or ""
    primary = _SUBTAG_SEPARATOR.split(declared.strip().lower())[0]
    return primary or None


def page_title(tree: LexborHTMLParser) -> str | None:
    """Return the collapsed ``<title>`` of the document head, or ``None`` when it is absent or blank."""
    node = tree.css_first("head > title")
    if node is None:
        return None
    return " ".join(node.text().split()) or None
