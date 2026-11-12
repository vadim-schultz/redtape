"""The canonical payload of a translated page: sorted-key JSON, so identical input gives byte-identical output."""

from __future__ import annotations

import json
from dataclasses import dataclass

from discovery_ingest.snapshot_translation.blocks import Block


@dataclass(frozen=True, slots=True)
class TranslatedPage:
    """A page ready to store: its blocks in document order with links restored, and how many kept their German text."""

    source_url: str
    source_hash: str
    truncated: bool
    blocks: tuple[Block, ...]
    untranslated: int


def _wire(block: Block) -> dict[str, str | list[str]]:
    """Return a block in the API's shape: a row carries its cells, every other kind its text."""
    if block.kind == "row":
        return {"kind": block.kind, "cells": list(block.texts)}
    return {"kind": block.kind, "text": block.texts[0]}


def canonical_payload(page: TranslatedPage) -> bytes:
    """Return ``page`` as UTF-8 JSON with sorted keys and no spaces, so equal pages give equal bytes."""
    body = {
        "unit": "snapshot",
        "source_hash": page.source_hash,
        "truncated": page.truncated,
        "source_url": page.source_url,
        "blocks": [_wire(block) for block in page.blocks],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
