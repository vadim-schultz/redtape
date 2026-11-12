"""The snapshot translation pipeline: stored HTML in, blocks of text out, and translated blocks back as a payload.

Every function here is pure. Fetching, the queue, the store and the engine calls live in other packages, and
``tests/test_snapshot_pure.py`` keeps HTTP clients, cloud SDKs and database drivers out of this one.
"""

from __future__ import annotations

from discovery_ingest.snapshot_translation.blocks import Block, Kind
from discovery_ingest.snapshot_translation.hash import source_hash
from discovery_ingest.snapshot_translation.page import SkippedPage, SourcePage, finish_page, prepare_page
from discovery_ingest.snapshot_translation.payload import TranslatedPage, canonical_payload
from discovery_ingest.snapshot_translation.skip import SkipReason
from discovery_ingest.snapshot_translation.validate_blocks import CheckedBlock, Rejected

__all__ = [
    "Block",
    "CheckedBlock",
    "Kind",
    "Rejected",
    "SkipReason",
    "SkippedPage",
    "SourcePage",
    "TranslatedPage",
    "canonical_payload",
    "finish_page",
    "prepare_page",
    "source_hash",
]
