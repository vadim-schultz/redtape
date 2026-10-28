"""One function per grounding rule; each takes the tally so every loss is counted."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import TypeVar

from discovery_ingest.extract.clean_links import absolute_web_url
from discovery_ingest.extract.llm.ground_state import Tally
from discovery_ingest.extract.llm.normalise import name_slug, normalise
from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem
from discovery_ingest.harvest.noise import is_noise

MAX_URL_LENGTH = 500


Q = TypeVar("Q", DocumentItem, DependencyItem)


def _quotes_page(quote: str, haystack: str) -> bool:
    needle = normalise(quote)
    return bool(needle) and needle in haystack


def keep_quoted(items: Sequence[Q], haystack: str, reason: str, tally: Tally) -> list[Q]:
    """Keep the items whose quote is on the page; ``haystack`` is the normalised page text."""
    kept = [item for item in items if _quotes_page(item.quote, haystack)]
    _lose_all([item for item in items if item not in kept], reason, tally)
    return kept


def _lose_all(items: Sequence[Q], reason: str, tally: Tally) -> None:
    for item in items:
        tally.lose(reason, item)


def ground_url(document: DocumentItem, links: Collection[str], tally: Tally) -> DocumentItem:
    """Return ``document`` with a ``url`` that is not a link of the page set to ``None``."""
    if document.url is None:
        return document
    url = absolute_web_url(document.url, "")
    if url in links and len(url) <= MAX_URL_LENGTH:
        return document.model_copy(update={"url": url})
    tally.urls_nulled += 1
    return document.model_copy(update={"url": None})


def _name_verdict(document: DocumentItem, seen: set[tuple[str, str]]) -> str | None:
    slug = name_slug(document.name)
    if is_noise(document.name) or not slug:
        return "noise"
    return "duplicate" if (slug, document.role) in seen else None


def keep_names(documents: Sequence[DocumentItem], tally: Tally) -> list[DocumentItem]:
    """Drop noise names and repeats of one ``(slug, role)``, keeping the first."""
    seen: set[tuple[str, str]] = set()
    kept: list[DocumentItem] = []
    for document in documents:
        verdict = _name_verdict(document, seen)
        if verdict is not None:
            tally.lose(verdict, document)
            continue
        seen.add((name_slug(document.name), document.role))
        kept.append(document)
    return kept


def _has_known_endpoints(dependency: DependencyItem, slugs: set[str]) -> bool:
    parent, requires = name_slug(dependency.parent), name_slug(dependency.requires)
    return parent != requires and parent in slugs and requires in slugs


def _once_per_pair(dependencies: Sequence[DependencyItem], tally: Tally) -> list[DependencyItem]:
    seen: set[tuple[str, str]] = set()
    kept: list[DependencyItem] = []
    for dependency in dependencies:
        pair = (name_slug(dependency.parent), name_slug(dependency.requires))
        if pair in seen:
            tally.lose("dependency_duplicate", dependency)
            continue
        seen.add(pair)
        kept.append(dependency)
    return kept


def keep_dependencies(
    dependencies: Sequence[DependencyItem], documents: Sequence[DocumentItem], haystack: str, tally: Tally
) -> list[DependencyItem]:
    """Keep dependencies between two different kept documents whose quote is on the page, once per pair."""
    slugs = {name_slug(document.name) for document in documents}
    linked = [dep for dep in dependencies if _has_known_endpoints(dep, slugs)]
    _lose_all([dep for dep in dependencies if dep not in linked], "dependency_endpoint", tally)
    return _once_per_pair(keep_quoted(linked, haystack, "dependency_quote", tally), tally)


def keep_codes(codes: Sequence[str], vocabulary: Collection[str], limit: int, tally: Tally) -> tuple[str, ...]:
    """Keep distinct codes of the vocabulary in order, count the others as unknown, and cap at ``limit``."""
    distinct = list(dict.fromkeys(codes))
    known = [code for code in distinct if code in vocabulary]
    tally.unknown_codes += len(distinct) - len(known)
    return tuple(known[:limit])
