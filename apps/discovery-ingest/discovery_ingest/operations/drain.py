"""Drain operation: the options of one worker drain, and the run that prepares its collaborators and returns the report."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import IngestSettings
from discovery_ingest.schemas import LLM_TASK_KINDS, WORKER_DEFAULT_TASK_KINDS, DiscoveryTaskKind, DrainReport
from discovery_ingest.worker.browser_setup import prepare_browser
from discovery_ingest.worker.capture_enqueue import enqueue_screenshot_for_mentions
from discovery_ingest.worker.drain_deps import DrainDeps
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_setup import prepare_llm, prepare_llm_enqueue
from discovery_ingest.worker.policy import MAX_TASKS_PER_CLAIM, DrainPolicy
from discovery_ingest.worker.run import run_recorded_drain

LLM_BATCH_SIZE = 5
"""Tasks per claim for an llm drain, so a stop releases at most four unstarted tasks."""

DEFAULT_BROWSER_BUDGET_SECONDS = 570.0


@dataclass(frozen=True, slots=True)
class DrainOptions:
    """The bounds and kinds of one drain as the operator gave them; ``None`` means the default for that bound.

    ``max_tasks=None`` is the default per claim: 5 when ``llm_extract`` is drained, else 50.
    """

    kinds: tuple[DiscoveryTaskKind, ...] = WORKER_DEFAULT_TASK_KINDS
    max_tasks: int | None = None
    max_batches: int = 1
    time_budget_seconds: float | None = None
    browser_budget_seconds: float | None = DEFAULT_BROWSER_BUDGET_SECONDS
    neuron_budget: float | None = None

    def policy(self) -> DrainPolicy:
        """Return the validated policy, or raise :class:`ValueError` naming the bound that is out of range."""
        drains_llm = any(kind in LLM_TASK_KINDS for kind in self.kinds)
        default_tasks = LLM_BATCH_SIZE if drains_llm else MAX_TASKS_PER_CLAIM
        return DrainPolicy(
            max_tasks=self.max_tasks if self.max_tasks is not None else default_tasks,
            max_batches=self.max_batches,
            time_budget_seconds=self.time_budget_seconds,
            kinds=self.kinds,
            browser_budget_seconds=self.browser_budget_seconds,
            neuron_budget=self.neuron_budget,
        )


def run_drain(options: DrainOptions, settings: IngestSettings, client: DiscoveryIngestClient) -> DrainReport:
    """Prepare the browser and the model when their kinds are drained, run the recorded drain and return its report.

    ``BrowserSetupError`` and ``LlmSetupError`` propagate, each with its ``exit_code``; nothing is printed.
    """
    policy = options.policy()
    llm_enqueue = prepare_llm_enqueue(settings, client, policy)
    with ExitStack() as stack:
        browser = (
            stack.enter_context(prepare_browser(settings, settings.user_agent, client))
            if policy.drains_browser_kinds
            else None
        )
        llm = prepare_llm(settings, client, stack) if policy.drains_llm_kinds else None
        deps = DrainDeps(
            client=client,
            fetcher=PoliteUrlFetcher(user_agent=settings.user_agent),
            browser=browser,
            llm=llm,
            after_extract=enqueue_screenshot_for_mentions,
            llm_enqueue=llm_enqueue,
            fim_base_url=settings.fim_portal_base_url,
            fused_screenshot=settings.render_fused_screenshot,
            screenshot_sweep_limit=settings.screenshot_sweep_limit,
        )
        return run_recorded_drain(deps, policy)
