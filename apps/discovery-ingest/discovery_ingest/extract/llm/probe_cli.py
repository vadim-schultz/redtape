"""The ``llm`` command: ``probe`` (a table per model, two Cloudflare variables) and ``eval`` (the gold set)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.llm.evaluation.command import register_eval_parser
from discovery_ingest.extract.llm.probe import run_probe
from discovery_ingest.extract.llm.probe_report import report_lines
from discovery_ingest.llm_settings import load_llm_settings

EXIT_REFUSED = 1
EXIT_USAGE = 2
DEFAULT_MAX_NEURONS = 900.0
MIN_INTERVAL_SECONDS = 1.0


def register_llm_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``llm`` command with its ``probe`` subcommand."""
    llm = sub.add_parser("llm", help="Cloudflare Workers AI")
    llm_sub = llm.add_subparsers(dest="llm_command")
    register_eval_parser(llm_sub)
    probe = llm_sub.add_parser("probe", help="Probe models on one fixture and print a table")
    probe.add_argument("--model", action="append", default=[], help="A Workers AI model id (repeatable)")
    probe.add_argument("--fixture", required=True, help="Path of a rendered HTML page to clean and send")
    probe.add_argument(
        "--max-neurons",
        type=float,
        default=DEFAULT_MAX_NEURONS,
        help=f"Stop before the next model once this many neurons are computed spent (default {DEFAULT_MAX_NEURONS:g})",
    )


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_USAGE


def llm_probe(args: argparse.Namespace) -> int:
    """Run the probe; exit 2 for missing settings, fixture or model, 1 when Cloudflare refused, else 0."""
    settings = load_llm_settings()
    if settings.missing_ai_credentials():
        return _fail(f"missing environment: {', '.join(settings.missing_ai_credentials())}")
    path, models = Path(args.fixture), args.model or [settings.llm_model]
    if not path.is_file():
        return _fail(f"fixture not found: {path}")
    if not all(models):
        return _fail("no model: pass --model <id> (repeatable) or set LLM_MODEL")
    throttle = Throttle(MIN_INTERVAL_SECONDS)
    html = decode_html(path.read_bytes(), None)
    with httpx.Client(trust_env=True) as http:
        report = run_probe(settings, models, html, http=http, throttle=throttle, max_neurons=args.max_neurons)
    print("\n".join(report_lines(report, settings)))
    return EXIT_REFUSED if report.refused else 0
