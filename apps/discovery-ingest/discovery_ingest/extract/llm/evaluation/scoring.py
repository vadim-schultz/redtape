"""Score one page: what the model said and what grounding kept, against the gold labels."""

from __future__ import annotations

from discovery_ingest.extract.llm.evaluation.gold import GoldPage
from discovery_ingest.extract.llm.evaluation.metrics import Counts, document_counts, edge_counts
from discovery_ingest.extract.llm.evaluation.results import Scores
from discovery_ingest.extract.llm.ground_state import Grounded
from discovery_ingest.extract.llm.schema import PageExtraction


def gold_codes(gold: GoldPage) -> tuple[str, ...]:
    """Return the domain and situation codes of the gold labels as one tuple."""
    return (*gold.domain_codes, *gold.situation_codes)


def _gold_counts(gold: GoldPage) -> tuple[Counts, Counts]:
    return Counts(0, 0, len(gold.documents)), Counts(0, 0, len(gold.dependencies))


def nothing_found(gold: GoldPage) -> Scores:
    """Return the scores of a page where the model said nothing usable: every gold item is missed."""
    documents, edges = _gold_counts(gold)
    return Scores(documents, edges, gold_codes=gold_codes(gold))


def score_page(gold: GoldPage, extraction: PageExtraction, grounded: Grounded) -> Scores:
    """Return the scores of the grounded answer, with the raw item count for the grounded rate."""
    documents = document_counts(
        [(d.name, d.role) for d in grounded.documents], [(d.name, d.role) for d in gold.documents]
    )
    edges = edge_counts(
        [(d.parent, d.requires) for d in grounded.dependencies], [(d.parent, d.requires) for d in gold.dependencies]
    )
    return Scores(
        documents,
        edges,
        raw_items=len(extraction.documents) + len(extraction.dependencies),
        kept_items=len(grounded.documents) + len(grounded.dependencies),
        predicted_codes=(*grounded.domain_codes, *grounded.situation_codes),
        gold_codes=gold_codes(gold),
        page_kind=extraction.page_kind,
    )
