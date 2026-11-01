"""What one page and one run produce: plain data that the summary, the table and the JSON file read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from discovery_ingest.extract.llm.evaluation.metrics import Counts
from discovery_ingest.extract.llm.ground_state import DroppedItem

PageStatus = Literal["ok", "invalid_output", "request_error", "empty_page"]


@dataclass(frozen=True, slots=True)
class Usage:
    """Tokens and neurons of one page; ``cached`` pages were paid for in an earlier run."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    neurons: float = 0.0
    cached: bool = False


@dataclass(frozen=True, slots=True)
class Scores:
    """How one page scored: counts, raw, surviving and quote-failed items, codes, the predicted kind and the items lost."""

    documents: Counts
    edges: Counts
    raw_items: int = 0
    kept_items: int = 0
    quote_failed_items: int = 0
    predicted_domain_codes: tuple[str, ...] = ()
    predicted_situation_codes: tuple[str, ...] = ()
    gold_domain_codes: tuple[str, ...] = ()
    gold_situation_codes: tuple[str, ...] = ()
    page_kind: str | None = None
    dropped: tuple[DroppedItem, ...] = ()


@dataclass(frozen=True, slots=True)
class PageResult:
    """One gold page after cleaning, the model call (when made) and grounding."""

    name: str
    status: PageStatus
    gold_kind: str
    cleaned_chars: int
    truncated: bool
    gold_names: int
    missing_names: tuple[str, ...]
    usage: Usage
    scores: Scores
    error: str | None = None

    @property
    def called_model(self) -> bool:
        """Whether a model answer (fresh or cached) stands behind this page."""
        return self.status in ("ok", "invalid_output") or self.usage.cached


@dataclass(frozen=True, slots=True)
class Stopped:
    """Why a run ended before the last page: a short ``reason`` and a message for the operator."""

    reason: str
    message: str


@dataclass(frozen=True, slots=True)
class EvalRun:
    """Every page that was run, the pages the gold set holds, why the run stopped early and the neurons it used."""

    pages: tuple[PageResult, ...]
    total_pages: int
    neurons_used: float
    stopped: Stopped | None = None
