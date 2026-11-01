"""Score one page: what the model said and what grounding kept, against the gold labels."""

from __future__ import annotations

from discovery_ingest.extract.llm.evaluation.drop_reasons import quote_failures
from discovery_ingest.extract.llm.evaluation.gold import GoldPage
from discovery_ingest.extract.llm.evaluation.metrics import Counts, document_counts, edge_counts
from discovery_ingest.extract.llm.evaluation.results import Scores
from discovery_ingest.extract.llm.ground import NON_PROCEDURE_KINDS
from discovery_ingest.extract.llm.ground_state import DroppedItem, Grounded
from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem, PageExtraction


def _gold_counts(gold: GoldPage) -> tuple[Counts, Counts]:
    return Counts(0, 0, len(gold.documents)), Counts(0, 0, len(gold.dependencies))


def nothing_found(gold: GoldPage) -> Scores:
    """Return the scores of a page where the model said nothing usable: every gold item is missed."""
    documents, edges = _gold_counts(gold)
    return Scores(documents, edges, gold_domain_codes=gold.domain_codes, gold_situation_codes=gold.situation_codes)


def lost_items(extraction: PageExtraction, grounded: Grounded) -> tuple[DroppedItem, ...]:
    """Return every item grounding lost; on a login or non-procedure page the whole answer is lost for its kind."""
    if extraction.page_kind in NON_PROCEDURE_KINDS:
        items: list[DocumentItem | DependencyItem] = [*extraction.documents, *extraction.dependencies]
        return tuple(DroppedItem("page_kind", item) for item in items)
    return grounded.diagnostics.dropped_items


def score_page(gold: GoldPage, extraction: PageExtraction, grounded: Grounded) -> Scores:
    """Return the scores of the grounded answer, with the raw, kept and quote-failed item counts for the two rates."""
    documents = document_counts(
        [(d.name, d.role) for d in grounded.documents], [(d.name, d.role) for d in gold.documents]
    )
    edges = edge_counts(
        [(d.parent, d.requires) for d in grounded.dependencies], [(d.parent, d.requires) for d in gold.dependencies]
    )
    dropped = lost_items(extraction, grounded)
    return Scores(
        documents,
        edges,
        raw_items=len(extraction.documents) + len(extraction.dependencies),
        kept_items=len(grounded.documents) + len(grounded.dependencies),
        quote_failed_items=quote_failures(dropped),
        predicted_domain_codes=grounded.domain_codes,
        predicted_situation_codes=grounded.situation_codes,
        gold_domain_codes=gold.domain_codes,
        gold_situation_codes=gold.situation_codes,
        page_kind=extraction.page_kind,
        dropped=dropped,
    )
