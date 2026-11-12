"""Extract the tokens a translation must keep: placeholders, numbers, dates, URLs, legal citations and markup."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from itertools import count

PLACEHOLDER = re.compile(r"\{[^{}\s]*\}|%\([A-Za-z_]+\)s|%[sd]")
PROTECTED = re.compile(r"⟦(\d+)⟧")
"""The opaque token a placeholder is replaced by before a machine call: ``⟦n⟧``, numbered in the order of the text."""
NUMBER = re.compile(r"\d+")
DATE = re.compile(r"(?<!\d)\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})(?!\d)")
URL = re.compile(r"(?:https?://|www\.)[^\s<>\"']+")
CITATION = re.compile(r"(?:§§?|Art\.)\s*\d+[a-z]?")
MARKUP = re.compile(r"<[^>]+>|\*\*|__|`|\[[^\]]*\]\([^)]*\)")
TRAILING_PUNCTUATION = ".,;:!?)]}"


def placeholders(text: str) -> Counter[str]:
    """Return the placeholders of ``text`` (``{name}``, ``%s``) with their counts."""
    return Counter(PLACEHOLDER.findall(text))


def protect(text: str) -> tuple[str, tuple[str, ...]]:
    """Replace each placeholder of ``text`` by a token ``⟦n⟧``; return that text and the placeholders in token order."""
    numbers_of_tokens = count()
    protected = PLACEHOLDER.sub(lambda _match: f"⟦{next(numbers_of_tokens)}⟧", text)
    return protected, tuple(PLACEHOLDER.findall(text))


def restore(text: str, placeholders: Sequence[str]) -> str:
    """Put each placeholder back where its token is; a token with no placeholder behind it stays in the text."""
    return PROTECTED.sub(lambda match: _placeholder_at(match, placeholders), text)


def _placeholder_at(match: re.Match[str], placeholders: Sequence[str]) -> str:
    index = int(match.group(1))
    return placeholders[index] if index < len(placeholders) else match.group(0)


def numbers(text: str) -> Counter[str]:
    """Return the digit runs of ``text`` without leading zeros, so ``1.000``, ``1,000`` and ``01`` compare by value."""
    return Counter(run.lstrip("0") or "0" for run in NUMBER.findall(text))


def dates(text: str) -> Counter[str]:
    """Return the numeric dates (``01.03.2025``) of ``text``."""
    return Counter(DATE.findall(text))


def urls(text: str) -> Counter[str]:
    """Return the URLs of ``text`` without the punctuation that ends a sentence."""
    return Counter(match.rstrip(TRAILING_PUNCTUATION) for match in URL.findall(text))


def citations(text: str) -> Counter[str]:
    """Return the legal citations (``§ 35``, ``Art. 5``) of ``text`` with the whitespace removed."""
    return Counter(re.sub(r"\s+", "", match) for match in CITATION.findall(text))


def markup(text: str) -> Counter[str]:
    """Return the markup tokens of ``text``: tags, bold, code and links."""
    return Counter(MARKUP.findall(text))
