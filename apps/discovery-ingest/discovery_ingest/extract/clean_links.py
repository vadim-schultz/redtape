"""Link rules of the page cleaner: absolute http(s) targets without fragments."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser

WEB_SCHEMES = frozenset({"http", "https"})


def absolute_web_url(href: str, base_url: str) -> str:
    """Return ``href`` resolved against ``base_url`` without its fragment, or ``""`` when it is not an http(s) page.

    An empty or fragment-only ``href`` points at the page itself and counts as no link.
    """
    target = href.strip()
    if not target or target.startswith("#"):
        return ""
    try:
        url, _fragment = urldefrag(urljoin(base_url, target))
        parts = urlsplit(url)
    except ValueError:
        return ""
    return url if parts.scheme in WEB_SCHEMES and parts.netloc else ""


def absolutize_links(tree: LexborHTMLParser, base_url: str) -> None:
    """Rewrite every anchor ``href`` in place to its absolute http(s) form, or to ``""`` when it is not a web page."""
    for anchor in tree.css("a[href]"):
        anchor.attrs["href"] = absolute_web_url(anchor.attributes.get("href") or "", base_url)


def link_set(tree: LexborHTMLParser) -> frozenset[str]:
    """Return every absolute http(s) target of the whole document; call after :func:`absolutize_links`."""
    return frozenset(href for anchor in tree.css("a[href]") if (href := anchor.attributes.get("href")))
