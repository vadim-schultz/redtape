"""The kind-to-handler table of one drain."""

from __future__ import annotations

from collections.abc import Mapping

from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.schemas import DiscoveryTaskKind
from discovery_ingest.worker.batch import TaskHandler
from discovery_ingest.worker.browser_spend import BrowserSpend
from discovery_ingest.worker.capture import CaptureScreenshotHandler
from discovery_ingest.worker.drain_deps import DrainDeps
from discovery_ingest.worker.enrich_metadata import EnrichMetadataHandler
from discovery_ingest.worker.extract import ExtractPageHandler
from discovery_ingest.worker.fetch_url import handle_fetch_url
from discovery_ingest.worker.harvest import handle_harvest_payload
from discovery_ingest.worker.llm_drain import LlmDrain
from discovery_ingest.worker.render import AfterSnapshot, RenderPageHandler

BrowserParts = tuple[BrowserClient | None, BrowserSpend | None, AfterSnapshot]
"""The browser port, its spend and the after-snapshot hook; the browser kinds are served only when the first two exist."""


def _browser_handlers(parts: BrowserParts) -> Mapping[DiscoveryTaskKind, TaskHandler]:
    browser, spend, hook = parts
    if browser is None or spend is None:
        return {}
    return {
        "render_page": RenderPageHandler(browser, spend, hook),
        "capture_screenshot": CaptureScreenshotHandler(browser, spend),
    }


def handler_table(
    deps: DrainDeps, browser: BrowserParts, llm_drain: LlmDrain | None
) -> Mapping[DiscoveryTaskKind, TaskHandler]:
    """Map each task kind to its handler; browser and llm kinds appear only when their parts exist."""
    llm_handlers = llm_drain.handlers() if llm_drain else {}
    return {
        "fetch_url": handle_fetch_url,
        "enrich_metadata": EnrichMetadataHandler(deps.fim_base_url),
        "harvest_payload": handle_harvest_payload,
        "extract_page": ExtractPageHandler(deps.extractors),
        **_browser_handlers(browser),
        **llm_handlers,
    }
