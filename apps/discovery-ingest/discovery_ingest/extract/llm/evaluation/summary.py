"""The numbers of a run: pooled precision and recall, grounded rate, tag agreement, cost and cleaner recall."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.extract.llm.evaluation.metrics import (
    Counts,
    grounded_rate,
    share_found,
    tag_agreement,
)
from discovery_ingest.extract.llm.evaluation.results import PageResult

FAILED = ("invalid_output", "request_error")


@dataclass(frozen=True, slots=True)
class Summary:
    """Every metric of one run; precision and recall pool the counts of all pages run."""

    pages_run: int
    failed_pages: int
    documents: Counts
    edges: Counts
    grounded_rate: float
    tag_agreement: float
    cleaner_recall: float
    page_kind_accuracy: float
    neurons_total: float
    neurons_per_page: float
    input_tokens: int
    output_tokens: int


def _pool(counts: list[Counts]) -> Counts:
    return sum(counts, Counts(0, 0, 0))


def _kind_accuracy(pages: list[PageResult]) -> float:
    judged = [page for page in pages if page.scores.page_kind is not None]
    return sum(page.scores.page_kind == page.gold_kind for page in judged) / len(judged) if judged else 1.0


def summarise(pages: tuple[PageResult, ...]) -> Summary:
    """Pool the pages of a run into one :class:`Summary`."""
    called = [page for page in pages if page.called_model]
    neurons = sum(page.usage.neurons for page in called)
    return Summary(
        pages_run=len(pages),
        failed_pages=sum(page.status in FAILED for page in pages),
        documents=_pool([page.scores.documents for page in pages]),
        edges=_pool([page.scores.edges for page in pages]),
        grounded_rate=grounded_rate(
            raw_items=sum(page.scores.raw_items for page in pages),
            kept_items=sum(page.scores.kept_items for page in pages),
        ),
        tag_agreement=tag_agreement([(page.scores.predicted_codes, page.scores.gold_codes) for page in pages]),
        cleaner_recall=share_found(
            total=sum(page.gold_names for page in pages), missing=sum(len(page.missing_names) for page in pages)
        ),
        page_kind_accuracy=_kind_accuracy(list(pages)),
        neurons_total=neurons,
        neurons_per_page=neurons / len(called) if called else 0.0,
        input_tokens=sum(page.usage.input_tokens or 0 for page in pages),
        output_tokens=sum(page.usage.output_tokens or 0 for page in pages),
    )
