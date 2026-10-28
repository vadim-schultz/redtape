"""Deterministic page cleaner: a rendered DOM becomes compact markdown plus its link set."""

from __future__ import annotations

from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser, LexborNode

from discovery_ingest.extract.clean_cap import cap_lines
from discovery_ingest.extract.clean_dom import drop_boilerplate, drop_widget_forms, main_region, preferred_region
from discovery_ingest.extract.clean_links import absolutize_links, link_set
from discovery_ingest.extract.clean_markdown import render_lines
from discovery_ingest.extract.clean_meta import page_language, page_title
from discovery_ingest.extract.clean_rank import span_of

CLEAN_VERSION = "clean-3"
DEFAULT_MAX_CHARS = 30_000
"""The one cap on cleaned text; the settings and the llm_extract handler import it."""


@dataclass(frozen=True)
class CleanPage:
    """The cleaned text of a page with the facts the grounding step needs."""

    text: str
    links: frozenset[str]
    language: str | None
    title: str | None
    truncated: bool
    version: str


def _body_lines(body: LexborNode) -> tuple[list[str], range | None]:
    drop_widget_forms(body)
    lines, inner = render_lines(body), preferred_region(body)
    return lines, None if inner is None else span_of(lines, render_lines(inner))


def _region_lines(tree: LexborHTMLParser) -> tuple[list[str], range | None]:
    drop_boilerplate(tree)
    region = main_region(tree)
    if region is None:
        return [], None
    return _body_lines(region) if region.tag == "body" else (render_lines(region), None)


def _clean_lines(tree: LexborHTMLParser) -> tuple[list[str], range | None]:
    """Return the page lines and the range of the main region; a DOM nested deeper than the interpreter can walk is empty."""
    try:
        return _region_lines(tree)
    except RecursionError:
        return [], None


def clean_page(html: str, base_url: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> CleanPage:
    """Return the compact markdown, link set and language of ``html``, resolved against ``base_url``."""
    tree = LexborHTMLParser(html)
    absolutize_links(tree, base_url)
    links, language, title = link_set(tree), page_language(tree), page_title(tree)
    lines, preferred = _clean_lines(tree)
    lines, truncated = cap_lines(lines, max_chars, preferred)
    return CleanPage("\n".join(lines), links, language, title, truncated, CLEAN_VERSION)
