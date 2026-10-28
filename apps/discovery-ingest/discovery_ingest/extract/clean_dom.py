"""DOM rules of the page cleaner: boilerplate removal and the choice of the main region."""

from __future__ import annotations

import re
from collections.abc import Iterator

from selectolax.lexbor import LexborHTMLParser, LexborNode

DROP_TAGS = ["script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside"]
HELPER_CLASSES = ("sr-only", "visually-hidden", "visuallyhidden", "screen-reader-text", "show-for-sr", "u-sr-only")
"""Whole class tokens of visually hidden helper text: spoken by screen readers, never page content."""
WIDGET_NAME = re.compile(r"(?<![a-z])(?:cookie|consent|search|breadcrumb)")
ATTRIBUTE_SELECTOR = "[hidden], [aria-hidden], [id], [class]"
MAIN_SELECTOR = "main, [role=main]"
MAIN_CONTENT_SELECTOR = f"{MAIN_SELECTOR}, article"
MAIN_MIN_CHARS = 600
WIDGET_FORM_SHARE = 0.5


def visible_text(node: LexborNode) -> str:
    """Return the text of ``node`` with every whitespace run collapsed to one space."""
    return " ".join(node.text(separator=" ").split())


def _is_hidden(node: LexborNode) -> bool:
    attributes = node.attributes
    return "hidden" in attributes or (attributes.get("aria-hidden") or "").lower() == "true"


def _is_widget(node: LexborNode) -> bool:
    if node.tag in ("html", "body"):
        return False
    name = f"{node.attributes.get('id') or ''} {node.attributes.get('class') or ''}"
    return WIDGET_NAME.search(name.lower()) is not None


def _holds_main_content(node: LexborNode) -> bool:
    """Return whether ``node`` is, or wraps, a main or article element."""
    return node.tag in ("main", "article") or node.css_first(MAIN_CONTENT_SELECTOR) is not None


def _is_helper_text(node: LexborNode) -> bool:
    if node.tag in ("html", "body") or _holds_main_content(node):
        return False
    return not set(HELPER_CLASSES).isdisjoint((node.attributes.get("class") or "").lower().split())


def _ancestors(node: LexborNode) -> Iterator[LexborNode]:
    parent = node.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def _outermost(nodes: list[LexborNode]) -> list[LexborNode]:
    """Drop every node that sits inside another listed node, so a removal never touches freed children."""
    chosen = set(nodes)
    return [node for node in nodes if not any(parent in chosen for parent in _ancestors(node))]


def drop_boilerplate(tree: LexborHTMLParser) -> None:
    """Remove scripts, page chrome, hidden and screen-reader-only elements and cookie, consent, search and breadcrumb widgets."""
    tree.strip_tags(DROP_TAGS)
    doomed = [
        node for node in tree.css(ATTRIBUTE_SELECTOR) if _is_hidden(node) or _is_widget(node) or _is_helper_text(node)
    ]
    for node in _outermost(doomed):
        node.decompose()


def _main_candidates(tree: LexborHTMLParser) -> Iterator[LexborNode]:
    yield from tree.css(MAIN_SELECTOR)[:1]
    articles = tree.css("article")
    if len(articles) == 1:
        yield articles[0]


def main_region(tree: LexborHTMLParser) -> LexborNode | None:
    """Return the main region when it holds enough text, else the body (``None`` when there is no body)."""
    for candidate in _main_candidates(tree):
        if len(visible_text(candidate)) >= MAIN_MIN_CHARS:
            return candidate
    return tree.body


def preferred_region(region: LexborNode) -> LexborNode | None:
    """Return the main element of ``region``, else its longest article, else ``None``."""
    for main in region.css(MAIN_SELECTOR)[:1]:
        return main
    articles = region.css("article")
    return max(articles, key=lambda article: len(visible_text(article)), default=None)


def drop_widget_forms(region: LexborNode) -> None:
    """Drop the forms of a body-wide region unless one wraps most of the page (an ASP.NET page form)."""
    total = len(visible_text(region))
    for form in _outermost(region.css("form")):
        if len(visible_text(form)) < total * WIDGET_FORM_SHARE:
            form.decompose()
