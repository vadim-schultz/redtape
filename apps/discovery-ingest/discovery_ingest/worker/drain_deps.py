"""Everything one worker drain is wired with, as one value instead of a long parameter list."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import DEFAULT_FIM_PORTAL_URL
from discovery_ingest.extract.base import Extractor
from discovery_ingest.extract.registry import EXTRACTORS
from discovery_ingest.worker.drain_loop import monotonic
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.llm_extract import AfterExtract, no_after_extract
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.render import AfterSnapshot


@dataclass(frozen=True, slots=True)
class DrainDeps:
    """The client, the fetcher and the optional collaborators one drain uses.

    ``browser`` and ``llm`` are required only when their kinds are drained; ``budget`` defaults to a guard over the
    client's ledger; ``fim_base_url`` is the portal the enrich handler links its entities to. ``fused_screenshot``
    makes a render take its HTML and screenshot from one call; it is off unless the operator turns it on.
    """

    client: DiscoveryIngestClient
    fetcher: PoliteUrlFetcher
    browser: BrowserClient | None = None
    llm: LlmResources | None = None
    after_extract: AfterExtract = no_after_extract
    llm_enqueue: LlmEnqueuer | None = None
    after_snapshot: AfterSnapshot | None = None
    extractors: Sequence[Extractor] = field(default=EXTRACTORS)
    budget: BudgetGuard | None = None
    clock: Callable[[], float] = monotonic
    fim_base_url: str = DEFAULT_FIM_PORTAL_URL
    fused_screenshot: bool = False
    screenshot_sweep_limit: int | None = None
