"""Pages through the pipeline.

``prepare_page`` turns stored HTML into a source page or a skip, and ``finish_page`` checks a translation of that source
page against it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.snapshot_translation.blocks import Block, page_blocks
from discovery_ingest.snapshot_translation.hash import source_hash
from discovery_ingest.snapshot_translation.limits import DOCUMENT_MAX_CHARS, MAX_BLOCKS
from discovery_ingest.snapshot_translation.payload import TranslatedPage
from discovery_ingest.snapshot_translation.skip import SkipReason, skip_reason
from discovery_ingest.snapshot_translation.urls import protect_urls
from discovery_ingest.snapshot_translation.validate_blocks import Rejected, check_page


@dataclass(frozen=True, slots=True)
class SourcePage:
    """A page ready for translation: its blocks with each link as a token, and the links the tokens stand for."""

    source_url: str
    source_hash: str
    truncated: bool
    blocks: tuple[Block, ...]
    urls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SkippedPage:
    """A page that is not translated: its source hash and the reason, which a skip marker stores."""

    source_hash: str
    reason: SkipReason


def prepare_page(html: str, source_url: str) -> SourcePage | SkippedPage:
    """Clean the stored ``html`` and return its blocks for translation, or the reason the page is skipped.

    ``source_url`` is the base the cleaner resolves links against. Empty or broken HTML is a skip, never an error.
    """
    page = clean_page(html, source_url, max_chars=DOCUMENT_MAX_CHARS)
    digest = source_hash(page.text)
    reason = skip_reason(page.text, page.language)
    if reason is not None:
        return SkippedPage(digest, reason)
    return _source_page(page, source_url, digest)


def _source_page(page: CleanPage, source_url: str, digest: str) -> SourcePage | SkippedPage:
    blocks = page_blocks(page.text)
    if not blocks:
        return SkippedPage(digest, SkipReason.TOO_SHORT)
    protected, urls = protect_urls(blocks[:MAX_BLOCKS])
    return SourcePage(source_url, digest, page.truncated or len(blocks) > MAX_BLOCKS, protected, urls)


def finish_page(source: SourcePage, translated: Sequence[Block]) -> TranslatedPage | Rejected:
    """Check ``translated`` blocks against ``source`` and return the page to store, or the reason it is refused."""
    checked = check_page(source.blocks, translated, source.urls)
    if isinstance(checked, Rejected):
        return checked
    return TranslatedPage(
        source.source_url,
        source.source_hash,
        source.truncated,
        tuple(item.block for item in checked),
        sum(item.untranslated for item in checked),
    )
