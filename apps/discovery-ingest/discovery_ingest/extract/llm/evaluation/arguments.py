"""The command line of ``llm eval``: its options and the checks that need no network."""

from __future__ import annotations

import argparse
from pathlib import Path

from discovery_ingest.config import IngestSettings
from discovery_ingest.extract.llm.prices import known_models
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION

DEFAULT_NEURON_BUDGET = 4000.0
DEFAULT_GOLD_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "gold"
DEFAULT_CACHE_DIR = Path(".llm-eval-cache")


def register_eval_parser(llm_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``llm eval`` to the ``llm`` command."""
    parser = llm_sub.add_parser("eval", help="Measure a model on the gold set and print a table")
    parser.add_argument("--model", required=True, help="A Workers AI model id with a price row")
    parser.add_argument(
        "--prompt-version", default=PROMPT_VERSION, help=f"The prompt version (default {PROMPT_VERSION})"
    )
    parser.add_argument("--limit", type=int, help="Only the first N gold pages by name")
    parser.add_argument("--out", help="Write the per-page results as JSON to this file")
    parser.add_argument(
        "--neuron-budget",
        type=float,
        default=DEFAULT_NEURON_BUDGET,
        help=f"Stop once this many neurons are used; the last call may pass it by its own cost (default {DEFAULT_NEURON_BUDGET:g})",
    )
    parser.add_argument("--gold-dir", default=str(DEFAULT_GOLD_DIR), help="Directory of the gold pages and labels")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="Directory of cached model answers")


def startup_problem(args: argparse.Namespace, settings: IngestSettings) -> str | None:
    """Return why the command cannot start (credentials, price row, prompt version), or ``None``."""
    if settings.missing_ai_credentials():
        return f"missing environment: {', '.join(settings.missing_ai_credentials())}"
    if args.model not in known_models():
        return f"no neuron price for model {args.model}; add a row to the price table first"
    if args.prompt_version != PROMPT_VERSION:
        return (
            f"this checkout builds prompt {PROMPT_VERSION}, not {args.prompt_version}; check out the commit that has it"
        )
    return None
