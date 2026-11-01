"""The printable table and the JSON file of a run."""

from __future__ import annotations

from collections.abc import Iterator

from discovery_ingest.extract.llm.evaluation.results import EvalRun, PageResult
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.evaluation.summary import Summary
from discovery_ingest.extract.llm.evaluation.targets import (
    DAILY_NEURON_CAP,
    METRIC_VERSION,
    MIN_DOMAIN_TAG_AGREEMENT,
    MIN_GROUNDED_RATE,
    MIN_PRECISION,
    MIN_RECALL,
    MIN_SITUATION_TAG_AGREEMENT,
)


def _page_row(page: PageResult) -> str:
    docs, items = page.scores.documents, page.scores
    tokens = f"{page.usage.input_tokens or 0}/{page.usage.output_tokens or 0}"
    status = f"{page.status} (cached)" if page.usage.cached else page.status
    return (
        f"| {page.name} | {items.page_kind or '-'} | {docs.correct}/{docs.predicted}/{docs.gold} "
        f"| {items.kept_items}/{items.raw_items} | {tokens} | {page.usage.neurons:.1f} | {status} |"
    )


def _verdict(value: float, minimum: float) -> str:
    return f"{value:.2f} | >= {minimum:.2f} ({'met' if value >= minimum else 'below'})"


def pages_per_day(neurons_per_page: float) -> float | None:
    """Return how many pages the daily cap pays for at ``neurons_per_page``, or ``None`` when it is not known."""
    return DAILY_NEURON_CAP / neurons_per_page if neurons_per_page > 0 else None


def _metric_rows(summary: Summary) -> Iterator[str]:
    yield f"| precision | {_verdict(summary.documents.precision, MIN_PRECISION)} |"
    yield f"| recall | {_verdict(summary.documents.recall, MIN_RECALL)} |"
    yield f"| edge precision | {summary.edges.precision:.2f} | |"
    yield f"| edge recall | {summary.edges.recall:.2f} | |"
    yield f"| quote-grounded rate | {_verdict(summary.grounded_rate, MIN_GROUNDED_RATE)} |"
    yield f"| kept rate | {summary.kept_rate:.2f} | |"
    yield f"| domain tag agreement | {_verdict(summary.domain_tag_agreement, MIN_DOMAIN_TAG_AGREEMENT)} |"
    yield f"| situation tag agreement | {_verdict(summary.situation_tag_agreement, MIN_SITUATION_TAG_AGREEMENT)} |"
    yield f"| cleaner recall | {summary.cleaner_recall:.2f} | |"
    yield f"| page kind accuracy | {summary.page_kind_accuracy:.2f} | |"
    yield f"| neurons per page | {summary.neurons_per_page:.1f} | |"
    per_day = pages_per_day(summary.neurons_per_page)
    yield f"| expected pages per day | {'-' if per_day is None else f'{per_day:.0f}'} | at {DAILY_NEURON_CAP} neurons |"


def table_lines(run: EvalRun, summary: Summary, setup: EvalSetup) -> list[str]:
    """Return the table: one row per page, then each metric with its starting target."""
    lines = [
        f"llm eval model={setup.model} prompt={setup.prompt_version} taxonomy={setup.taxonomy.digest()} {METRIC_VERSION}",
        f"pages run {len(run.pages)} of {run.total_pages}, failed {summary.failed_pages}",
        "| page | kind | docs correct/predicted/gold | items kept/raw | tokens in/out | neurons | status |",
        *map(_page_row, run.pages),
        "| metric | value | target |",
        *_metric_rows(summary),
        f"tokens in {summary.input_tokens} out {summary.output_tokens}; neurons used this run {run.neurons_used:.1f}",
    ]
    if run.stopped:
        lines.append(f"stopped ({run.stopped.reason}): {run.stopped.message}")
    return lines
