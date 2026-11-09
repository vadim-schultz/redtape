"""The JSON file of a run: the summary and, per page, the scores, the usage and what was lost."""

from __future__ import annotations

from pydantic import JsonValue

from discovery_ingest.extract.llm.evaluation.metrics import Counts
from discovery_ingest.extract.llm.evaluation.report import pages_per_day
from discovery_ingest.extract.llm.evaluation.results import EvalRun, PageResult
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.evaluation.summary import Summary
from discovery_ingest.extract.llm.evaluation.targets import METRIC_VERSION
from discovery_ingest.extract.llm.ground_state import DroppedItem
from discovery_ingest.extract.llm.schema import DependencyItem


def _counts(counts: Counts) -> dict[str, JsonValue]:
    return {"correct": counts.correct, "predicted": counts.predicted, "gold": counts.gold}


def _summary(summary: Summary) -> dict[str, JsonValue]:
    return {
        "pages_run": summary.pages_run,
        "failed_pages": summary.failed_pages,
        "precision": summary.documents.precision,
        "recall": summary.documents.recall,
        "edge_precision": summary.edges.precision,
        "edge_recall": summary.edges.recall,
        "grounded_rate": summary.grounded_rate,
        "kept_rate": summary.kept_rate,
        "category_tag_agreement": summary.category_tag_agreement,
        "cleaner_recall": summary.cleaner_recall,
        "page_kind_accuracy": summary.page_kind_accuracy,
        "neurons_total": summary.neurons_total,
        "neurons_per_page": summary.neurons_per_page,
        "expected_pages_per_day": pages_per_day(summary.neurons_per_page),
        "input_tokens": summary.input_tokens,
        "output_tokens": summary.output_tokens,
    }


def _dropped(dropped: DroppedItem) -> dict[str, JsonValue]:
    kind = "dependency" if isinstance(dropped.item, DependencyItem) else "document"
    return {"reason": dropped.reason, "kind": kind, "item": dropped.item.model_dump(mode="json")}


def _page(page: PageResult) -> dict[str, JsonValue]:
    scores, usage = page.scores, page.usage
    return {
        "name": page.name,
        "status": page.status,
        "error": page.error,
        "gold_kind": page.gold_kind,
        "page_kind": scores.page_kind,
        "cleaned_chars": page.cleaned_chars,
        "truncated": page.truncated,
        "cached": usage.cached,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "neurons": usage.neurons,
        "documents": _counts(scores.documents),
        "edges": _counts(scores.edges),
        "raw_items": scores.raw_items,
        "kept_items": scores.kept_items,
        "quote_failed_items": scores.quote_failed_items,
        "predicted_category_codes": list(scores.predicted_category_codes),
        "gold_category_codes": list(scores.gold_category_codes),
        "missing_from_cleaned_text": list(page.missing_names),
        "dropped": [_dropped(item) for item in scores.dropped],
    }


def json_report(run: EvalRun, summary: Summary, setup: EvalSetup) -> dict[str, JsonValue]:
    """Return the report as JSON-ready data."""
    return {
        "model": setup.model,
        "prompt_version": setup.prompt_version,
        "taxonomy_digest": setup.taxonomy.digest(),
        "metric_version": METRIC_VERSION,
        "total_pages": run.total_pages,
        "neurons_used": run.neurons_used,
        "stopped": {"reason": run.stopped.reason, "message": run.stopped.message} if run.stopped else None,
        "summary": _summary(summary),
        "pages": [_page(page) for page in run.pages],
    }
