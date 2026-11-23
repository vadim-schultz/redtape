"""Fakes for the pipeline tests: stage processes that answer like the drains, and a machine client for the plan reads."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from discovery_ingest.budget_models import BudgetRow, BudgetSnapshot
from discovery_ingest.embedding_models import EmbeddingSummary
from discovery_ingest.operations.pipeline import STAGES
from discovery_ingest.schemas import (
    DrainReport,
    SnapshotLocaleSummary,
    SnapshotSummaryResponse,
    StopReason,
    TaskSummary,
)
from discovery_ingest.translation_models import TranslationLocaleSummary, TranslationSummary


def stage_of(argv: Sequence[str]) -> str:
    """Return the id of the stage whose command line ``argv`` is, by its command and its fixed flags."""
    for spec in STAGES:
        if tuple(argv[: len(spec.command)]) == spec.command and all(token in argv for token in spec.flags):
            return spec.id
    raise AssertionError(f"no stage for {list(argv)}")


def report_line(*, succeeded: bool = True, stop_reason: StopReason = "queue_empty", claimed: int = 0) -> str:
    """Return the one-line JSON report a drain prints on stdout."""
    report = DrainReport(
        claimed=claimed, completed=claimed, failed=0, skipped=0, stop_reason=stop_reason, succeeded=succeeded
    )
    return report.model_dump_json()


@dataclass
class Behaviour:
    """How a fake stage answers: the stdout it prints, its exit code, and an optional hook run while it is waited on."""

    stdout: str | None = field(default_factory=report_line)
    exit_code: int = 0
    on_wait: Callable[[], None] | None = None


class FakeStage:
    """A stage process: it prints its behaviour's stdout and exits with its exit code once it is waited on."""

    def __init__(self, argv: list[str], behaviour: Behaviour, events: list[str]) -> None:
        """Remember the command line, what the stage answers and the shared event log."""
        self.argv = argv
        self.stage = stage_of(argv)
        self.returncode: int | None = None
        self.signals: list[int] = []
        self._behaviour = behaviour
        self._events = events

    def communicate(self, timeout: float | None = None) -> tuple[str | None, None]:
        """Run the wait hook, then finish with the behaviour's stdout and exit code."""
        if self._behaviour.on_wait is not None:
            self._behaviour.on_wait()
        self._events.append(f"end:{self.stage}")
        self.returncode = self._behaviour.exit_code
        return self._behaviour.stdout, None

    def send_signal(self, signum: int) -> None:
        """Record the signal the orchestrator forwarded."""
        self.signals.append(signum)

    def budget_seconds(self) -> float:
        """Return the value of ``--time-budget-seconds`` on the command line."""
        return float(self.argv[self.argv.index("--time-budget-seconds") + 1])


class FakeSpawner:
    """Starts :class:`FakeStage` processes and keeps the start and end events in order."""

    def __init__(self, behaviours: dict[str, Behaviour] | None = None) -> None:
        """Keep the behaviour of each stage id; a stage without one succeeds with an empty queue."""
        self.behaviours = behaviours or {}
        self.events: list[str] = []
        self.processes: list[FakeStage] = []

    def __call__(self, argv: Sequence[str]) -> FakeStage:
        """Record the start and return the process for ``argv``."""
        stage = stage_of(argv)
        self.events.append(f"start:{stage}")
        process = FakeStage(list(argv), self.behaviours.get(stage, Behaviour()), self.events)
        self.processes.append(process)
        return process

    def started(self) -> list[str]:
        """Return the stage ids started, in start order."""
        return [process.stage for process in self.processes]

    def process(self, stage: str) -> FakeStage:
        """Return the first process started for ``stage``."""
        return next(process for process in self.processes if process.stage == stage)


class FakeMachine:
    """Answers the plan reads from fixed numbers and counts every read by its route."""

    def __init__(
        self,
        *,
        ready_by_kinds: dict[str, int] | None = None,
        embeddings: int = 0,
        cards: dict[str, int] | None = None,
        pages: int = 0,
        budget_rows: list[BudgetRow] | None = None,
        missing: int = 0,
    ) -> None:
        """Set the numbers each route answers with; ``ready_by_kinds`` is keyed by the comma joined kinds."""
        self.calls: Counter[str] = Counter()
        self._ready = ready_by_kinds or {}
        self._embeddings = embeddings
        self._cards = cards or {}
        self._pages = pages
        self._rows = budget_rows or []
        self._missing = missing
        self.tasks = SimpleNamespace(summary=self._task_summary)
        self.embeddings = SimpleNamespace(summary=self._embedding_summary)
        self.translations = SimpleNamespace(summary=self._translation_summary)
        self.snapshots = SimpleNamespace(summary=self._snapshot_summary)
        self.budget = SimpleNamespace(snapshot=self._budget)
        self.artifacts = SimpleNamespace(missing_screenshot=self._missing_screenshot)

    def _task_summary(self, *, kinds: Sequence[str]) -> TaskSummary:
        key = ",".join(kinds)
        self.calls[f"tasks:{key}"] += 1
        return TaskSummary(
            pending_ready=self._ready.get(key, 0), pending_delayed=0, claimed=0, claimed_stale=0, completed=0, failed=0
        )

    def _embedding_summary(self, model: str) -> EmbeddingSummary:
        self.calls["embeddings"] += 1
        return EmbeddingSummary(pending_ready=self._embeddings, claimed=0, failed=0, stale_candidates=0)

    def _translation_summary(self) -> TranslationSummary:
        self.calls["translations"] += 1
        rows = [
            TranslationLocaleSummary(locale=locale, pending_ready=count, claimed=0, failed=0, stale=0, translated=0)
            for locale, count in self._cards.items()
        ]
        return TranslationSummary(locales=rows)

    def _snapshot_summary(self) -> SnapshotSummaryResponse:
        self.calls["snapshots"] += 1
        row = SnapshotLocaleSummary(
            locale="tr", pending_ready=self._pages, claimed=0, failed=0, translated=0, stale=0, skipped=0
        )
        return SnapshotSummaryResponse(locales=[row])

    def _budget(self) -> BudgetSnapshot:
        self.calls["budget"] += 1
        return BudgetSnapshot(items=self._rows)

    def _missing_screenshot(self, *, limit: int, catalogue_service_id: Any = None) -> SimpleNamespace:
        self.calls["missing_screenshot"] += 1
        return SimpleNamespace(items=[object()] * min(self._missing, limit))


def row(resource: str, remaining: float, *, exhausted: bool = False) -> BudgetRow:
    """Return one ledger row with ``remaining`` left of a cap of 1000."""
    return BudgetRow(
        resource=resource,  # type: ignore[arg-type]
        period="2026-11",
        cap=1000,
        used=1000 - remaining,
        remaining=remaining,
        exhausted=exhausted,
    )
