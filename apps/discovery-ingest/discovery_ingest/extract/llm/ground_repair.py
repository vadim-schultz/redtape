"""Deterministic repair of percent-encoded model text, applied to an item before grounding."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import TypeVar
from urllib.parse import unquote

from discovery_ingest.extract.llm.ground_state import Tally
from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem

MIN_SEQUENCES = 2
TEXT_FIELDS = ("name", "quote", "condition", "parent", "requires")

_SEQUENCE = re.compile(r"%[0-9A-Fa-f]{2}")

Item = TypeVar("Item", DocumentItem, DependencyItem)


def _utf8_or_none(text: str) -> str | None:
    try:
        return unquote(text, errors="strict")
    except UnicodeDecodeError:
        return None


def _has_control(text: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in text)


def percent_decoded(text: str) -> str:
    """Return ``text`` decoded as UTF-8 when it has two or more ``%XX`` sequences and decodes cleanly, else ``text``."""
    if len(_SEQUENCE.findall(text)) < MIN_SEQUENCES:
        return text
    decoded = _utf8_or_none(text)
    return text if decoded is None or _has_control(decoded) else decoded


def repair_item(item: Item) -> Item:
    """Return ``item`` with its name, quote and condition fields decoded; urls are not text fields and stay as written."""
    texts = {field: getattr(item, field, None) for field in TEXT_FIELDS}
    update = {field: percent_decoded(value) for field, value in texts.items() if value}
    return item.model_copy(update=update)


def repair_all(items: Sequence[Item], tally: Tally) -> list[Item]:
    """Return the repaired ``items`` and count each item that changed once in ``tally.repaired``."""
    repaired = [repair_item(item) for item in items]
    tally.repaired += sum(new != old for new, old in zip(repaired, items, strict=True))
    return repaired
