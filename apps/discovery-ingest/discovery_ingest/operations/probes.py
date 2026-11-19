"""The three probes: ``browser probe``, ``llm probe`` and ``fim probe``. Each returns the table lines and whether it failed."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from discovery_ingest.browser.canary_run import canary_lines, run_canary
from discovery_ingest.browser.client import CloudflareBrowserClient
from discovery_ingest.browser.probe import run_probe as run_browser_probe_plan
from discovery_ingest.browser.probe_plan import probe_plan
from discovery_ingest.browser.probe_report import report_lines as browser_report_lines
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.config import BrowserSettings, load_bot_settings
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.llm.probe import run_probe as run_llm_probe_plan
from discovery_ingest.extract.llm.probe_report import report_lines as llm_report_lines
from discovery_ingest.fim.probe import gate_passed, probe_keys, probe_lines
from discovery_ingest.llm_settings import LlmSettings
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

LLM_MIN_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True, slots=True)
class ProbeOutcome:
    """The table lines to print and whether the probe failed (Cloudflare refused, or the FIM gate did not pass)."""

    lines: list[str]
    failed: bool


def plain_size(url: str) -> int | None:
    """Return the byte size of a polite plain GET of ``url`` (no credentials involved), or ``None`` when it failed."""
    outcome = PoliteUrlFetcher(user_agent=load_bot_settings().user_agent).get(url)
    return outcome.byte_length if not outcome.failed else None


def browser_probe(
    settings: BrowserSettings,
    *,
    urls: Sequence[str],
    error_urls: Sequence[str],
    variants: Sequence[str] | None,
    max_browser_seconds: float,
) -> ProbeOutcome:
    """Call each quick action of the plan for every URL and report the table."""
    chosen = None if variants is None else list(variants)
    plan = probe_plan(list(urls), list(error_urls), user_agent=load_bot_settings().user_agent, variants=chosen)
    throttle = Throttle(settings.browser_min_interval_seconds)
    with httpx.Client() as http:
        report = run_browser_probe_plan(
            settings,
            plan,
            http=http,
            throttle=throttle,
            max_ms=round(max_browser_seconds * 1000),
            plain_size=plain_size,
        )
    return ProbeOutcome(browser_report_lines(report, settings), report.refused)


def canary_probe(
    settings: BrowserSettings, *, urls: Sequence[str], required: int, max_browser_seconds: float
) -> ProbeOutcome:
    """Compare /content with the fused /snapshot on ``required`` stable pages from ``urls``; fails when the canary does."""
    with httpx.Client(trust_env=True) as http:
        client = CloudflareBrowserClient(settings, user_agent=load_bot_settings().user_agent, http=http)
        run = run_canary(client, urls, required=required, max_ms=round(max_browser_seconds * 1000))
    return ProbeOutcome(canary_lines(run), not run.verdict.passed)


def llm_probe(settings: LlmSettings, *, models: Sequence[str], fixture: Path, max_neurons: float) -> ProbeOutcome:
    """Clean the fixture, send it to each model and report the table."""
    throttle = Throttle(LLM_MIN_INTERVAL_SECONDS)
    html = decode_html(fixture.read_bytes(), None)
    with httpx.Client(trust_env=True) as http:
        report = run_llm_probe_plan(settings, list(models), html, http=http, throttle=throttle, max_neurons=max_neurons)
    return ProbeOutcome(llm_report_lines(report, settings), report.refused)


def fim_probe(base_url: str, keys: Sequence[str]) -> ProbeOutcome:
    """Fetch each steckbrief and report its status; the probe fails when the gate does not pass."""
    fetcher = PoliteUrlFetcher(user_agent=load_bot_settings().user_agent)
    results = probe_keys(fetcher, base_url, list(keys))
    return ProbeOutcome(probe_lines(results), not gate_passed(results))
