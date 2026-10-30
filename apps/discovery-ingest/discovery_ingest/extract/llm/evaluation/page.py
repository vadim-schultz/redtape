"""The values one page passes between the steps of a run: its context, a reply, a failure or a stop."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.evaluation.gold import GoldPage
from discovery_ingest.extract.llm.evaluation.metrics import absent_names
from discovery_ingest.extract.llm.evaluation.results import PageResult, PageStatus, Scores, Stopped, Usage
from discovery_ingest.extract.llm.evaluation.scoring import nothing_found
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable


class StopRun(Exception):
    """The run must end before the last page; the pages done so far are still reported."""

    def __init__(self, reason: str, message: str) -> None:
        """Keep the short ``reason`` and the ``message`` for the operator."""
        super().__init__(message)
        self.stopped = Stopped(reason, message)


def _budget_stop(budget: float, used: float) -> StopRun:
    return StopRun(
        "budget", f"the neuron budget of {budget:g} is reached ({used:.1f} used): raise --neuron-budget to go on"
    )


def refusal_stop(answer: Denied | LedgerUnavailable, budget: float, used: float) -> StopRun:
    """Return the stop for a refused reservation, saying whether the run budget, the ledger or its outage did it."""
    match answer:
        case Denied(reason="run_budget"):
            return _budget_stop(budget, used)
        case Denied():
            return StopRun("ledger", "the day's neuron ledger has too few neurons left for the next page")
        case _:
            return StopRun(
                "ledger_unavailable", "the budget ledger stopped answering; no page is sent without a reservation"
            )


@dataclass(frozen=True, slots=True)
class Failure:
    """A page the model did not answer usably; the run goes on."""

    status: PageStatus
    error: str


@dataclass(frozen=True, slots=True)
class Reply:
    """A model answer and what it cost."""

    result: LlmResult
    usage: Usage


@dataclass(frozen=True, slots=True)
class PageContext:
    """A gold page and its cleaned text, with the builders of its result."""

    gold: GoldPage
    cleaned: CleanPage

    def result(self, status: PageStatus, usage: Usage, scores: Scores, error: str | None = None) -> PageResult:
        """Return the result of this page with the gold names the cleaned text lost."""
        names = [document.name for document in self.gold.documents]
        return PageResult(
            name=self.gold.name,
            status=status,
            gold_kind=self.gold.page_kind,
            cleaned_chars=len(self.cleaned.text),
            truncated=self.cleaned.truncated,
            gold_names=len(names),
            missing_names=tuple(absent_names(names, self.cleaned.text)),
            usage=usage,
            scores=scores,
            error=error,
        )

    def failed(self, failure: Failure, usage: Usage | None = None) -> PageResult:
        """Return the result of a page where nothing usable came back: every gold item is missed."""
        return self.result(failure.status, usage or Usage(), nothing_found(self.gold), failure.error)
