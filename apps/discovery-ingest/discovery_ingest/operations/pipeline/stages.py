"""The stages the daily pipeline runs: each one's command, fixed flags, allotment cap and floor, and the phases.

Data only. A stage is ``python -m discovery_ingest <command>`` with these flags; the caps come from the plan. A phase
starts only after the one before it ends. The final pass runs every stage that still has ready work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

PHASE_ONE: tuple[str, ...] = ("seed", "render", "embed", "card_translation", "page_translation")
"""Fetch and drain, the browser render (one process), embedding and the Azure card and page translation."""
PHASE_TWO: tuple[str, ...] = ("extract_page", "llm", "capture", "card_tail")
"""Rules extraction (it reads what render stored), llm_extract with concurrency, the screenshot sweeper and the tail."""
FINAL_PHASE = 3
"""The final pass: every stage with ready work left after phase two, each run under the time that is left."""


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One stage: its id, the command it runs, its fixed flags, and the allotment its cap draws on.

    ``resource`` names the allotment whose headroom caps the stage (``None``: no cap flag); ``cap`` is the most it may
    take and ``floor`` the least worth starting with.
    """

    id: str
    command: tuple[str, ...]
    flags: tuple[str, ...]
    resource: str | None = None
    cap_flag: str | None = None
    cap: float = 0.0
    floor: float = 0.0

    def argv(self, caps: Mapping[str, float], seconds: float) -> list[str]:
        """Return the arguments after ``python -m discovery_ingest`` for this stage under ``caps`` and ``seconds``."""
        cap_args: list[str] = []
        if self.resource is not None and self.cap_flag is not None:
            cap_args = [self.cap_flag, f"{caps[self.resource]:g}"]
        return [*self.command, *self.flags, "--time-budget-seconds", f"{seconds:g}", *cap_args]


STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        id="seed",
        command=("worker", "drain"),
        flags=("--max-tasks", "50", "--max-batches", "20", "--kinds", "fetch_url,enrich_metadata,harvest_payload"),
    ),
    StageSpec(
        id="render",
        command=("worker", "drain"),
        flags=("--max-tasks", "5", "--max-batches", "40", "--kinds", "render_page"),
        resource="browser_seconds",
        cap_flag="--browser-budget-seconds",
        cap=570.0,
        floor=30.0,
    ),
    StageSpec(
        id="embed",
        command=("embed", "drain"),
        flags=("--max-tasks", "50", "--max-batches", "60"),
        resource="neurons",
        cap_flag="--neuron-budget",
        cap=3000.0,
        floor=100.0,
    ),
    StageSpec(
        id="card_translation",
        command=("translate", "drain"),
        flags=("--unit", "card", "--engine", "azure-translator", "--max-tasks", "10", "--max-batches", "60"),
    ),
    StageSpec(
        id="page_translation",
        command=("translate", "drain"),
        flags=("--unit", "snapshot", "--max-tasks", "5", "--max-batches", "60"),
    ),
    StageSpec(
        id="extract_page",
        command=("worker", "drain"),
        flags=("--max-tasks", "50", "--max-batches", "20", "--kinds", "extract_page"),
    ),
    StageSpec(
        id="llm",
        command=("worker", "drain"),
        flags=("--max-tasks", "5", "--max-batches", "20", "--concurrency", "3", "--kinds", "llm_extract"),
        resource="neurons",
        cap_flag="--neuron-budget",
        cap=2500.0,
        floor=300.0,
    ),
    StageSpec(
        id="capture",
        command=("worker", "drain"),
        flags=("--max-tasks", "5", "--max-batches", "40", "--kinds", "capture_screenshot"),
        resource="browser_seconds",
        cap_flag="--browser-budget-seconds",
        cap=570.0,
        floor=30.0,
    ),
    StageSpec(
        id="card_tail",
        command=("translate", "drain"),
        flags=("--unit", "card", "--engine", "llm", "--max-tasks", "10", "--max-batches", "60"),
        resource="neurons",
        cap_flag="--neuron-budget",
        cap=2500.0,
        floor=100.0,
    ),
)
"""Every stage in run order: the first phase's stages, then the second's. Caps are granted in this order."""

STAGE_IDS: tuple[str, ...] = tuple(spec.id for spec in STAGES)
"""Every stage id, in run order."""


@dataclass(frozen=True, slots=True)
class Phase:
    """One phase: the number its stage records carry, and the stages it may plan."""

    number: int
    stage_ids: tuple[str, ...]


PHASES: tuple[Phase, ...] = (Phase(1, PHASE_ONE), Phase(2, PHASE_TWO), Phase(FINAL_PHASE, STAGE_IDS))
"""The phases in run order."""
FIRST_PASS: Mapping[str, int] = {stage: phase.number for phase in PHASES[:2] for stage in phase.stage_ids}
"""Each stage of the first two phases, mapped to its phase: the stages the plan command shows."""


def stage_by_id(stage_id: str) -> StageSpec:
    """Return the stage named ``stage_id``; a name that is not a stage raises :class:`KeyError`."""
    return next(spec for spec in STAGES if spec.id == stage_id)
