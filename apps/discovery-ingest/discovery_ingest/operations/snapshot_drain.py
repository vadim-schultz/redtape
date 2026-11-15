"""``translate drain --unit snapshot``: the Azure engine, the document share of the monthly character ledger, and the report.

Before anything is claimed, the monthly ledger must be readable and hold more than the card band, ``1 − share`` of the
cap. The share follows the pending demand of documents and cards, and never exceeds the ceiling, which is the card band's
complement. A run spends at most today's pace: the ledger's remainder over the days left in the anchored window (UTC), so
what a day leaves unspent is in the next day's allowance. Each page's reservation may not take the ledger below the
larger of the two floors, so documents never take the card band and never more than today's pace.
"""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
CARD_BAND_SHARE: Final = 0.4
"""The share of the monthly cap that cards always keep, whatever the documents' demand."""
DEFAULT_DOCUMENT_BUDGET_SHARE: Final = 0.6
"""The documents' ceiling: the most of the monthly cap they may take, ``1 − CARD_BAND_SHARE``."""
SNAPSHOT_MIN_INTERVAL_SECONDS: Final = 1.0
DEFAULT_WINDOW_ANCHOR: Final = date(2026, 11, 13)
"""The first day of the Azure allowance's window, in UTC, as the operator reported it. The monthly rule that follows from
it (the window restarts on this day of each month) is inferred, not confirmed by the portal."""


class DocumentShareSettings(BaseSettings):
    """``AZURE_DOCUMENT_BUDGET_SHARE``, read from the worker's environment only: the documents' ceiling."""

    model_config = SettingsConfigDict(extra="ignore")

    share: float = Field(
        default=DEFAULT_DOCUMENT_BUDGET_SHARE, ge=0.0, le=1.0, validation_alias="AZURE_DOCUMENT_BUDGET_SHARE"
    )


class PacingSettings(BaseSettings):
    """``AZURE_WINDOW_ANCHOR`` and ``AZURE_DAILY_CHAR_PACE``, read from the worker's environment only.

    The anchor is the first day of the window (UTC). The pace, when set, replaces the computed daily allowance.
    """

    model_config = SettingsConfigDict(extra="ignore")

    window_anchor: date = Field(default=DEFAULT_WINDOW_ANCHOR, validation_alias="AZURE_WINDOW_ANCHOR")
    daily_pace: float | None = Field(default=None, gt=0, validation_alias="AZURE_DAILY_CHAR_PACE")


def document_budget_share() -> float:
    """Return the documents' ceiling from the environment, or the default; a value outside 0 to 1 raises ``ValueError``."""
    return DocumentShareSettings().share


def load_pacing_settings() -> PacingSettings:
    """Return the pacing settings from the environment; an anchor that is not a date raises ``ValueError``."""
    return PacingSettings()


def adaptive_share(documents: int, cards: int, ceiling: float) -> float:
    """Return the documents' share of the monthly cap: their part of the pending demand, never above ``ceiling``.

    With no pending demand the ceiling stands; the drain claims nothing in that case anyway.
    """
    demand = documents + cards
    return ceiling if demand == 0 else min(ceiling, documents / demand)


def _month_index(day: date) -> int:
    return day.year * 12 + day.month - 1


def _boundary(anchor: date, months: int) -> date:
    """Return the window boundary ``months`` months after ``anchor``'s month, on the anchor's day or the month's last day."""
    year, month = divmod(_month_index(anchor) + months, 12)
    return date(year, month + 1, min(anchor.day, monthrange(year, month + 1)[1]))


def window_end(anchor: date, today: date) -> date:
    """Return the first day after the anchored window that holds ``today``: the next boundary after it."""
    months = _month_index(today) - _month_index(anchor)
    while _boundary(anchor, months) <= today:
        months += 1
    while _boundary(anchor, months - 1) > today:
        months -= 1
    return _boundary(anchor, months)


def days_left(anchor: date, today: date) -> int:
    """Return the days from ``today`` to the end of the window that holds it, ``today`` included."""
    return (window_end(anchor, today) - today).days


def daily_allowance(remaining: float, *, anchor: date, today: date, daily_pace: float | None = None) -> float:
    """Today's characters: the ledger's remainder over the days left, or ``daily_pace`` when a setting names it.

    The remainder already holds what earlier days left unspent, so the unspent amount carries over with no separate ledger.
    """
    if daily_pace is not None:
        return min(remaining, daily_pace)
    return remaining / days_left(anchor, today)


def _utc_today() -> date:
    return datetime.now(UTC).date()


@dataclass(frozen=True, slots=True)
class Pacing:
    """The window and the daily pace a snapshot drain spends by: the anchor, the optional pace setting and the day's clock."""

    anchor: date = DEFAULT_WINDOW_ANCHOR
    daily_pace: float | None = None
    today: Callable[[], date] = _utc_today


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
    """The machine client, the engine, the document share, the clock of its time budget and the pacing of one drain."""

    client: DiscoveryIngestClient
    engine: TranslationEngine
    share: float = DEFAULT_DOCUMENT_BUDGET_SHARE
    clock: Callable[[], float] = monotonic
    pacing: Pacing = Pacing()


def _document_meter(guard: BudgetGuard, share: float, pacing: Pacing) -> UsageMeter | None:
    """Return the meter that keeps the card band and today's pace, or ``None`` when nothing may be spent.

    An unreadable ledger raises :class:`LlmSetupError`: nothing is claimed or fetched without a proof of the floors.
    """
    left = guard.remaining(CHARACTER_RESOURCE)
    if left.remaining is None or left.cap is None:
        raise LlmSetupError(
            f"cannot read the {CHARACTER_RESOURCE} budget ledger (GET /machine/budgets); snapshot drain will not spend",
            EXIT_NOT_READY,
        )
    allowance = daily_allowance(
        left.remaining, anchor=pacing.anchor, today=pacing.today(), daily_pace=pacing.daily_pace
    )
    floor = max((1.0 - share) * left.cap, left.remaining - allowance)
    if left.exhausted or left.remaining <= floor:
        return None
    return FlooredMeter(CharacterMeter(guard), guard, Floor(CHARACTER_RESOURCE, floor))


def run_snapshot_drain(deps: SnapshotDeps, policy: DrainPolicy) -> DrainReport:
    """Claim, translate and settle page batches until ``policy`` or a stop ends the drain; return the report.

    With the documents' share or today's pace used up nothing is claimed, and the drain ends at once with ``llm_budget``.
    """
    guard = BudgetGuard(deps.client.budget)
    meter = _document_meter(guard, deps.share, deps.pacing)
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


def _share_of(client: DiscoveryIngestClient) -> float:
    """Return the documents' share from the pending demand of both queues; an unreadable queue leaves the ceiling in place."""
    ceiling = min(document_budget_share(), 1.0 - CARD_BAND_SHARE)
    documents = remaining_of(lambda: client.snapshots.summary().pending_ready)
    cards = remaining_of(lambda: client.translations.summary().pending_ready)
    if documents is None or cards is None:
        return ceiling
    return adaptive_share(documents, cards, ceiling)


def _pacing_of_environment() -> Pacing:
    try:
        settings = load_pacing_settings()
    except ValueError as err:
        raise LlmSetupError(f"invalid pacing settings: {err}", EXIT_MISSING_SETTINGS) from err
    return Pacing(anchor=settings.window_anchor, daily_pace=settings.daily_pace)


def run_snapshot(options: SnapshotOptions, client: DiscoveryIngestClient) -> DrainReport:
    """Build the Azure engine from the environment, then run the snapshot drain as a ``snapshot_translate`` run."""
    policy = options.policy()
    pacing = _pacing_of_environment()
    with httpx.Client(trust_env=True) as http:
        deps = SnapshotDeps(client, _azure_engine(http), _share_of(client), pacing=pacing)
        return run_recorded(client, "snapshot_translate", lambda: run_snapshot_drain(deps, policy))
