"""``translate drain --unit snapshot``: the Azure engine, the document share of the monthly character ledger, and the report.

Before anything is claimed, the monthly ledger must be readable and hold more than the card band, ``1 − share`` of the
cap. Each page's reservation may not take the ledger below that floor, so documents never take the card band.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import MAX_SNAPSHOT_BATCH, DrainReport
from discovery_ingest.translation.character_meter import CharacterMeter
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.locale_codes import UnmappedLocaleError
from discovery_ingest.translation.meter import CHARACTER_RESOURCE, UsageMeter
from discovery_ingest.translation.registry import EngineConfig, UnknownEngineError, build_engine
from discovery_ingest.worker.drain_loop import Finish, drain_until_stop, monotonic
from discovery_ingest.worker.floored_meter import Floor, FlooredMeter
from discovery_ingest.worker.llm_setup import EXIT_MISSING_SETTINGS, EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.report import build_report, remaining_of
from discovery_ingest.worker.run import run_recorded
from discovery_ingest.worker.snapshot_batch import SnapshotContext, run_snapshot_batch
from discovery_ingest.worker.tally import Tally

AZURE_ENGINE: Final = "azure-translator"
DEFAULT_DOCUMENT_BUDGET_SHARE: Final = 0.6
"""Documents' share of the monthly cap; the other 40% stays for cards and interface strings."""
SNAPSHOT_MIN_INTERVAL_SECONDS: Final = 1.0


class DocumentShareSettings(BaseSettings):
    """``AZURE_DOCUMENT_BUDGET_SHARE``, read from the worker's environment only."""

    model_config = SettingsConfigDict(extra="ignore")

    share: float = Field(
        default=DEFAULT_DOCUMENT_BUDGET_SHARE, ge=0.0, le=1.0, validation_alias="AZURE_DOCUMENT_BUDGET_SHARE"
    )


def document_budget_share() -> float:
    """Return the document share from the environment, or the default; a value outside 0 to 1 raises ``ValueError``."""
    return DocumentShareSettings().share


@dataclass(frozen=True, slots=True)
class SnapshotOptions:
    """The bounds of one snapshot drain as the operator gave them: pages per claim (at most five) and how many claims."""

    max_tasks: int = MAX_SNAPSHOT_BATCH
    max_batches: int = 1
    time_budget_seconds: float | None = None

    def policy(self) -> DrainPolicy:
        """Return the validated policy, or raise :class:`ValueError` naming the bound that is out of range."""
        if not 1 <= self.max_tasks <= MAX_SNAPSHOT_BATCH:
            raise ValueError(f"max_tasks must be between 1 and {MAX_SNAPSHOT_BATCH} for snapshot pages")
        return DrainPolicy(
            max_tasks=self.max_tasks, max_batches=self.max_batches, time_budget_seconds=self.time_budget_seconds
        )


@dataclass(frozen=True, slots=True)
class SnapshotDeps:
    """The machine client, the engine and the document share of one snapshot drain, and the clock of its time budget."""

    client: DiscoveryIngestClient
    engine: TranslationEngine
    share: float = DEFAULT_DOCUMENT_BUDGET_SHARE
    clock: Callable[[], float] = monotonic


def _document_meter(guard: BudgetGuard, share: float) -> UsageMeter | None:
    """Return the meter that keeps the card band, or ``None`` when the documents' share is already used up.

    An unreadable ledger raises :class:`LlmSetupError`: nothing is claimed or fetched without a proof of the floor.
    """
    left = guard.remaining(CHARACTER_RESOURCE)
    if left.remaining is None or left.cap is None:
        raise LlmSetupError(
            f"cannot read the {CHARACTER_RESOURCE} budget ledger (GET /machine/budgets); snapshot drain will not spend",
            EXIT_NOT_READY,
        )
    floor = (1.0 - share) * left.cap
    if left.exhausted or left.remaining <= floor:
        return None
    return FlooredMeter(CharacterMeter(guard), guard, Floor(CHARACTER_RESOURCE, floor))


def run_snapshot_drain(deps: SnapshotDeps, policy: DrainPolicy) -> DrainReport:
    """Claim, translate and settle page batches until ``policy`` or a stop ends the drain; return the report.

    With the documents' share used up nothing is claimed, and the drain ends at once with ``llm_budget``.
    """
    guard = BudgetGuard(deps.client.budget)
    meter = _document_meter(guard, deps.share)
    tally = Tally()
    if meter is None:
        finish = Finish("llm_budget")
    else:
        ctx = SnapshotContext(deps.client, deps.engine, meter, policy, tally)
        finish = drain_until_stop(lambda: run_snapshot_batch(ctx), policy, deps.clock)
    tally.characters_used = 0 if meter is None else round(meter.used)
    tally.ledger_unavailable = guard.ledger_unavailable
    return build_report(tally, finish, remaining_of(lambda: deps.client.snapshots.summary().pending_ready))


def _azure_engine(http: httpx.Client) -> TranslationEngine:
    try:
        return build_engine(AZURE_ENGINE, EngineConfig(http=http, min_interval_seconds=SNAPSHOT_MIN_INTERVAL_SECONDS))
    except (ValueError, UnknownEngineError, UnmappedLocaleError) as err:
        raise LlmSetupError(f"translation engine {AZURE_ENGINE!r} cannot start: {err}", EXIT_MISSING_SETTINGS) from err


def run_snapshot(options: SnapshotOptions, client: DiscoveryIngestClient) -> DrainReport:
    """Build the Azure engine from the environment, then run the snapshot drain as a ``snapshot_translate`` run."""
    policy = options.policy()
    share = document_budget_share()
    with httpx.Client(trust_env=True) as http:
        deps = SnapshotDeps(client, _azure_engine(http), share)
        return run_recorded(client, "snapshot_translate", lambda: run_snapshot_drain(deps, policy))
