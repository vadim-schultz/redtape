"""``browser probe``: call each quick action the worker will use and print a table; needs only the two Cloudflare variables."""

from __future__ import annotations

import argparse
import sys

import httpx

from discovery_ingest.browser.probe import run_probe
from discovery_ingest.browser.probe_plan import VARIANTS, probe_plan
from discovery_ingest.browser.probe_report import report_lines
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.config import load_bot_settings, load_browser_settings
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

EXIT_REFUSED = 1
EXIT_MISSING_SETTINGS = 2
DEFAULT_MAX_BROWSER_SECONDS = 240.0


def plain_size(url: str) -> int | None:
    """Return the byte size of a polite plain GET of ``url`` (no credentials involved), or ``None`` when it failed."""
    outcome = PoliteUrlFetcher(user_agent=load_bot_settings().user_agent).get(url)
    return outcome.byte_length if not outcome.failed else None


def register_browser_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``browser`` command with its ``probe`` subcommand."""
    browser = sub.add_parser("browser", help="Cloudflare Browser Run")
    browser_sub = browser.add_subparsers(dest="browser_command")
    probe = browser_sub.add_parser("probe", help="Call every quick action the worker uses and print a table")
    probe.add_argument("--url", action="append", default=[], help="A page to render with every variant (repeatable)")
    probe.add_argument("--error-url", action="append", default=[], help="A page expected to fail; contract call only")
    probe.add_argument("--variant", action="append", choices=VARIANTS, help="Only these variants (default all)")
    probe.add_argument(
        "--max-browser-seconds",
        type=float,
        default=DEFAULT_MAX_BROWSER_SECONDS,
        help=f"Stop once this many browser seconds are spent (default {DEFAULT_MAX_BROWSER_SECONDS:g})",
    )


def browser_probe(args: argparse.Namespace) -> int:
    """Run the probe plan; exit 2 when a Cloudflare variable is missing, 1 when Cloudflare refused."""
    settings = load_browser_settings()
    if settings.missing_credentials():
        print(f"missing environment: {', '.join(settings.missing_credentials())}", file=sys.stderr)
        return EXIT_MISSING_SETTINGS
    user_agent = load_bot_settings().user_agent
    plan = probe_plan(args.url, args.error_url, user_agent=user_agent, variants=args.variant)
    throttle = Throttle(settings.browser_min_interval_seconds)
    with httpx.Client() as http:
        report = run_probe(
            settings,
            plan,
            http=http,
            throttle=throttle,
            max_ms=round(args.max_browser_seconds * 1000),
            plain_size=plain_size,
        )
    print("\n".join(report_lines(report, settings)))
    return EXIT_REFUSED if report.refused else 0
