"""Eval metrics as pure functions on plain data: names, roles and codes in, scores out."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from discovery_ingest.extract.llm.normalise import name_slug

Mention = tuple[str, str]
"""A document as ``(name, role)``."""
Edge = tuple[str, str]
"""A dependency as ``(parent name, required name)``."""
Key = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Counts:
    """Correct, predicted and gold items of one page or of many pages pooled."""

    correct: int
    predicted: int
    gold: int

    @property
    def precision(self) -> float:
        """Correct over predicted; nothing predicted is vacuously precise."""
        return self.correct / self.predicted if self.predicted else 1.0

    @property
    def recall(self) -> float:
        """Correct over gold; nothing expected is vacuously recalled."""
        return self.correct / self.gold if self.gold else 1.0

    def __add__(self, other: Counts) -> Counts:
        """Pool two pages by summing the tallies."""
        return Counts(self.correct + other.correct, self.predicted + other.predicted, self.gold + other.gold)


def _counts(predicted: set[Key], gold: set[Key]) -> Counts:
    return Counts(len(predicted & gold), len(predicted), len(gold))


def document_counts(predicted: Iterable[Mention], gold: Iterable[Mention]) -> Counts:
    """Match documents by the promotion slug of the name and then the role."""
    return _counts(_document_keys(predicted), _document_keys(gold))


def edge_counts(predicted: Iterable[Edge], gold: Iterable[Edge]) -> Counts:
    """Match dependencies by the slugs of the parent and the required document, in that direction."""
    return _counts(_edge_keys(predicted), _edge_keys(gold))


def _document_keys(documents: Iterable[Mention]) -> set[Key]:
    return {(name_slug(name), role) for name, role in documents}


def _edge_keys(edges: Iterable[Edge]) -> set[Key]:
    return {(name_slug(parent), name_slug(required)) for parent, required in edges}


def grounded_rate(*, raw_items: int, kept_items: int) -> float:
    """Return the share of raw model items that survived grounding; no items at all is a full rate."""
    if kept_items > raw_items:
        raise ValueError(f"more items kept than raw: {kept_items} of {raw_items}")
    return kept_items / raw_items if raw_items else 1.0


def _jaccard(predicted: Collection[str], gold: Collection[str]) -> float:
    union = set(predicted) | set(gold)
    return len(set(predicted) & set(gold)) / len(union) if union else 1.0


def tag_agreement(pages: Sequence[tuple[Collection[str], Collection[str]]]) -> float:
    """Return the mean Jaccard overlap of predicted and gold codes per page; empty against empty agrees."""
    return sum(_jaccard(predicted, gold) for predicted, gold in pages) / len(pages) if pages else 1.0
