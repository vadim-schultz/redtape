"""Spot login walls: pages and URLs no crawl should touch."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from selectolax.lexbor import LexborHTMLParser

_LOGIN_TOKENS = ("login", "signin", "openid-connect")
_AUTH = re.compile(r"(?<![a-z0-9])auth(?![a-z0-9])")


def url_looks_like_login(url: str) -> bool:
    """Whether the host or path says login: ``login``, ``signin`` or ``openid-connect`` anywhere, ``auth`` as a word.

    ``auth`` is matched as a whole word so ``/author/profile`` is not a login page.
    """
    parts = urlsplit(url.lower())
    text = f"{parts.netloc}{parts.path}"
    return any(token in text for token in _LOGIN_TOKENS) or _AUTH.search(text) is not None


def has_password_input(html: str) -> bool:
    """Whether the DOM contains an ``input`` of type ``password`` (any letter case)."""
    return any(
        (node.attributes.get("type") or "").lower() == "password" for node in LexborHTMLParser(html).css("input")
    )
