"""Measure how often translation memory would hit, from an export of stored snapshot blocks. Measurement only.

The export is JSON lines, one stored snapshot translation per line::

    {"locale": "en", "page": "<id>", "blocks": ["Reisepass beantragen", "Gebühren", ...]}

``blocks`` holds the cleaned source text of each block of the page. Every text is hashed after Unicode normalisation (NFC)
and whitespace collapse, so the same sentence hashes alike across pages. The report gives:

- ``distinct_block_hashes``: how many different texts the export holds;
- ``shared_across_locales``: the share of those texts that occur in more than one locale;
- ``memory_hit_rate``: the share of block occurrences whose (text, locale) pair already appeared earlier in the export.
  A memory table keyed by text and target locale would have served those without a call.

The probe calls no service and writes nothing. Whether a memory table is built is decided from its output.

Usage::

    python scripts/translation_memory_probe.py <export.jsonl>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Record:
    """One stored snapshot translation: its target locale, its page id and the source text of each block."""

    locale: str
    page: str
    blocks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Measurement:
    """What the export shows: its size, the distinct texts, and the two shares the decision needs."""

    pages: int
    locales: tuple[str, ...]
    occurrences: int
    distinct_block_hashes: int
    shared_across_locales: float
    memory_hit_rate: float


def block_hash(text: str) -> str:
    """The identity of a block's text: its NFC form with every run of whitespace collapsed to one space, hashed."""
    normal = _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()
    return hashlib.sha256(normal.encode("utf-8")).hexdigest()


def record_of(line: str, number: int) -> Record:
    """Parse one export line; a line that is not a stored snapshot translation names its line number."""
    try:
        raw = json.loads(line)
        blocks = raw["blocks"]
        if not isinstance(raw["locale"], str) or not isinstance(raw["page"], str) or not isinstance(blocks, list):
            raise TypeError("locale and page must be strings and blocks a list")
        return Record(raw["locale"], raw["page"], tuple(str(block) for block in blocks))
    except (ValueError, KeyError, TypeError) as err:
        raise ValueError(f"line {number} is not a stored snapshot translation: {err}") from err


def read_records(lines: Iterable[str]) -> list[Record]:
    """Parse every non-blank line of the export, in order."""
    return [record_of(line, number) for number, line in enumerate(lines, start=1) if line.strip()]


def _share(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def _locales_by_hash(records: Sequence[Record]) -> dict[str, set[str]]:
    locales: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for block in record.blocks:
            locales[block_hash(block)].add(record.locale)
    return locales


def _memory_hits(records: Sequence[Record]) -> int:
    seen: set[tuple[str, str]] = set()
    hits = 0
    for record in records:
        for block in record.blocks:
            key = (block_hash(block), record.locale)
            hits += key in seen
            seen.add(key)
    return hits


def measure(records: Sequence[Record]) -> Measurement:
    """Return the measurement of ``records``; an empty export measures zero everywhere."""
    locales = _locales_by_hash(records)
    occurrences = sum(len(record.blocks) for record in records)
    shared = sum(1 for names in locales.values() if len(names) > 1)
    return Measurement(
        pages=len(records),
        locales=tuple(sorted({record.locale for record in records})),
        occurrences=occurrences,
        distinct_block_hashes=len(locales),
        shared_across_locales=round(_share(shared, len(locales)), 4),
        memory_hit_rate=round(_share(_memory_hits(records), occurrences), 4),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Read the export named by the first argument and print the measurement as JSON."""
    parser = argparse.ArgumentParser(description="Measure the translation-memory hit rate of stored snapshot blocks.")
    parser.add_argument("export", help="JSON-lines export of stored snapshot translations")
    args = parser.parse_args(argv)
    with open(args.export, encoding="utf-8") as handle:
        try:
            records = read_records(handle)
        except ValueError as err:
            print(f"translation_memory_probe: {err}", file=sys.stderr)
            return 2
    print(json.dumps(asdict(measure(records)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
