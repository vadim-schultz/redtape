"""Deterministic grounding: keep only what quotes the page and fits the vocabulary."""

from __future__ import annotations

from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.ground_rules import (
    ground_url,
    keep_codes,
    keep_dependencies,
    keep_names,
    keep_quoted,
)
from discovery_ingest.extract.llm.ground_state import Diagnostics, Grounded, Tally
from discovery_ingest.extract.llm.normalise import normalise
from discovery_ingest.extract.llm.schema import MAX_DOMAIN_CODES, MAX_SITUATION_CODES, DocumentItem, PageExtraction
from discovery_ingest.extract.llm.taxonomy import Taxonomy

NON_PROCEDURE_KINDS = frozenset({"login_or_error", "other"})

__all__ = ["Diagnostics", "Grounded", "ground"]


def _documents(extraction: PageExtraction, clean_page: CleanPage, haystack: str, tally: Tally) -> list[DocumentItem]:
    quoted = keep_quoted(extraction.documents, haystack, "quote", tally)
    return keep_names([ground_url(item, clean_page.links, tally) for item in quoted], tally)


def ground(extraction: PageExtraction, clean_page: CleanPage, vocab: Taxonomy) -> Grounded:
    """Return the documents, dependencies and codes of ``extraction`` that ``clean_page`` and ``vocab`` support."""
    tally = Tally()
    if extraction.page_kind in NON_PROCEDURE_KINDS:
        return Grounded((), (), (), (), tally.freeze(extraction.page_kind))
    haystack = normalise(clean_page.text)
    documents = _documents(extraction, clean_page, haystack, tally)
    dependencies = keep_dependencies(extraction.dependencies, documents, haystack, tally)
    domains = keep_codes(extraction.domain_codes, vocab.domain_codes, MAX_DOMAIN_CODES, tally)
    situations = keep_codes(extraction.situation_codes, vocab.situation_codes, MAX_SITUATION_CODES, tally)
    return Grounded(tuple(documents), tuple(dependencies), domains, situations, tally.freeze(extraction.page_kind))
