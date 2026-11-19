"""Fused-render canary comparison: does the fused /snapshot DOM read like the /content DOM of the same page (chapter 8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.extract.clean import clean_page
from discovery_ingest.snapshot_translation.hash import source_hash

IDENTITY_FLOOR = 0.9
"""The share of pages whose cleaned-text hash must match exactly."""
MAX_TEXT_LOSS = 0.05
"""The largest share of its cleaned text any page may lose in the fused DOM."""


@dataclass(frozen=True, slots=True)
class PageCompare:
    """What the canary measured on one page: hash identity, text loss, and block and link counts of both DOMs."""

    identical: bool
    text_loss: float
    content_blocks: int
    fused_blocks: int
    content_links: int
    fused_links: int

    @property
    def lost_link(self) -> bool:
        """Whether the fused DOM has fewer links than the /content DOM."""
        return self.fused_links < self.content_links


@dataclass(frozen=True, slots=True)
class CanaryVerdict:
    """The gate's answer: how many pages were measured, how many matched exactly, and whether the gate passed."""

    pages: int
    identical: int
    passed: bool


def page_hash(html: str, base_url: str) -> str:
    """Return the source hash of the cleaned text of ``html``, the identity the worker stores pages by."""
    return source_hash(clean_page(html, base_url).text)


def compare_page(content_html: str, fused_html: str, base_url: str) -> PageCompare:
    """Clean both DOMs the way the worker does and measure what the gate reads."""
    content = clean_page(content_html, base_url)
    fused = clean_page(fused_html, base_url)
    return PageCompare(
        identical=source_hash(content.text) == source_hash(fused.text),
        text_loss=_text_loss(content.text, fused.text),
        content_blocks=_blocks(content.text),
        fused_blocks=_blocks(fused.text),
        content_links=len(content.links),
        fused_links=len(fused.links),
    )


def judge(pages: Sequence[PageCompare], *, required: int) -> CanaryVerdict:
    """Pass when ``required`` pages were measured, IDENTITY_FLOOR of them match, and no page breaks MAX_TEXT_LOSS or a link."""
    identical = sum(page.identical for page in pages)
    enough = bool(pages) and len(pages) >= required
    matched = enough and identical / len(pages) >= IDENTITY_FLOOR
    intact = all(page.text_loss <= MAX_TEXT_LOSS and not page.lost_link for page in pages)
    return CanaryVerdict(pages=len(pages), identical=identical, passed=matched and intact)


def _text_loss(content: str, fused: str) -> float:
    """Return the share of the /content text the fused DOM lacks; zero when the fused DOM has all of it or more."""
    if not content:
        return 0.0
    return max(0.0, (len(content) - len(fused)) / len(content))


def _blocks(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())
