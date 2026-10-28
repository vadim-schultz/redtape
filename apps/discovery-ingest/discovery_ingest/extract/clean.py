"""Deterministic page cleaner: a rendered DOM becomes compact markdown plus its link set."""

from __future__ import annotations

from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser

from discovery_ingest.extract.clean_dom import drop_boilerplate, drop_widget_forms, main_region
from discovery_ingest.extract.clean_links import absolutize_links, link_set
from discovery_ingest.extract.clean_markdown import render_lines
from discovery_ingest.extract.clean_meta import page_language, page_title

CLEAN_VERSION = "clean-1"
DEFAULT_MAX_CHARS = 12000


@dataclass(frozen=True)
class CleanPage:
    """The cleaned text of a page with the facts the grounding step needs."""

    text: str
    links: frozenset[str]
    language: str | None
    title: str | None
    truncated: bool
    version: str


def _region_lines(tree: LexborHTMLParser) -> list[str]:
    drop_boilerplate(tree)
    region = main_region(tree)
    if region is None:
        return []
    if region.tag == "body":
        drop_widget_forms(region)
    return render_lines(region)


def _clean_lines(tree: LexborHTMLParser) -> list[str]:
    """Return the page lines; a DOM nested deeper than the interpreter can walk reads as an empty page."""
    try:
        return _region_lines(tree)
    except RecursionError:
        return []


def clean_page(html: str, base_url: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> CleanPage:
    """Return the compact markdown, link set and language of ``html``, resolved against ``base_url``."""
    tree = LexborHTMLParser(html)
    absolutize_links(tree, base_url)
    links, language, title = link_set(tree), page_language(tree), page_title(tree)
    lines = _clean_lines(tree)
    return CleanPage("\n".join(lines), links, language, title, False, CLEAN_VERSION)
