"""CLI entry points for discovery ingest workers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from discovery_ingest.artifacts_cli import artifacts_download, artifacts_list, register_artifacts_parser
from discovery_ingest.browser.probe_cli import browser_probe, register_browser_parser
from discovery_ingest.budget_cli import budget_report_minutes, budget_show, register_budget_parser
from discovery_ingest.candidate_emit import DEFAULT_EMIT_LIMIT, EmitSelection, emit_report, preview_report
from discovery_ingest.candidates_cli import candidates_page, register_candidates_aids
from discovery_ingest.capture_requeue import capture_requeue, register_capture_parser
from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.config import (
    DEFAULT_FIM_PORTAL_URL,
    IngestSettings,
    load_bot_settings,
    load_ingest_settings,
)
from discovery_ingest.curation_command import candidates_curate
from discovery_ingest.extract.llm.evaluation.command import llm_eval
from discovery_ingest.extract.llm.probe_cli import llm_probe, register_llm_parser
from discovery_ingest.fim.client import FixtureSteckbriefSource
from discovery_ingest.fim.keys import STECKBRIEF_KEY_PATTERN
from discovery_ingest.fim.probe import gate_passed, probe_keys, probe_lines
from discovery_ingest.govdata.ckan import GovDataCkanClient, GovDataCkanError
from discovery_ingest.leika.client import FixtureStammtextSource
from discovery_ingest.llm_requeue import llm_requeue
from discovery_ingest.operations.catalogue import (
    CatalogueSource,
    GovDataCkanSource,
    GovDataFileSource,
    NothingToIngest,
    PvogSource,
    ingest,
)
from discovery_ingest.operations.drain import DrainOptions, run_drain
from discovery_ingest.operations.enrich import (
    CatalogueRowNotFound,
    Enricher,
    EnrichError,
    FimEnricher,
    LeikaEnricher,
    catalogue_row,
    run_enrich,
)
from discovery_ingest.operations.results import IngestResult
from discovery_ingest.pvog.client import PvogClient, PvogClientError
from discovery_ingest.schemas import (
    TASK_KINDS,
    WORKER_DEFAULT_TASK_KINDS,
    DiscoveryTaskKind,
    is_task_kind,
)
from discovery_ingest.worker.browser_setup import BrowserSetupError
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_setup import LlmSetupError


def main(argv: list[str] | None = None) -> int:
    """Run a discovery ingest subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get((args.command, getattr(args, f"{args.command}_command", None)))
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


LookupT = TypeVar("LookupT")
DocT = TypeVar("DocT")


def _print_skip(message: str) -> None:
    print(f"skip row: {message}", file=sys.stderr)


def _ingest(source: CatalogueSource, settings: IngestSettings) -> IngestResult:
    with DiscoveryIngestClient.from_settings(settings) as client:
        return ingest(source, client, on_skip=_print_skip)


def _govdata_run(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    source = GovDataFileSource(Path(args.input), args.jurisdiction_id)
    try:
        _ingest(source, settings)
    except NothingToIngest as err:
        print(err, file=sys.stderr)
        return 1
    except DiscoveryMachineApiError:
        return 1
    return 0


def _govdata_fetch(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    ckan = GovDataCkanClient(
        settings.govdata_ckan_base_url,
        settings.govdata_package_id,
        scope_ars=settings.govdata_open_pvog_ars,
    )
    source = GovDataCkanSource(
        ckan,
        args.jurisdiction_id,
        max_pages=args.max_pages,
        page_size=args.page_size,
        max_records=args.max_records,
    )
    try:
        _ingest(source, settings)
    except GovDataCkanError as err:
        print(f"govdata fetch failed: {err}", file=sys.stderr)
        return 1
    except NothingToIngest as err:
        print(err, file=sys.stderr)
        return 1
    except DiscoveryMachineApiError as err:
        print(err, file=sys.stderr)
        return 1
    return 0


def _pvog_run(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    source = PvogSource(PvogClient(settings.pvog_api_base_url), args.jurisdiction_id, max_pages=args.max_pages)
    try:
        _ingest(source, settings)
    except PvogClientError as err:
        print(err, file=sys.stderr)
        return 1
    except NothingToIngest as err:
        print(err, file=sys.stderr)
        return 1
    except DiscoveryMachineApiError:
        return 1
    return 0


def _enrich(enricher: Enricher[LookupT, DocT], catalogue: CatalogueExportItem) -> int:
    """Post one enrichment; print the operator message and exit 1 on a known failure."""
    settings = load_ingest_settings()
    try:
        with DiscoveryIngestClient.from_settings(settings) as api:
            run_enrich(enricher, catalogue, api)
    except EnrichError as err:
        print(err, file=sys.stderr)
        return 1
    except DiscoveryMachineApiError:
        return 1
    return 0


def _fim_enrich(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    try:
        catalogue = catalogue_row(Path(args.catalogue_export), args.catalogue_service_id)
    except CatalogueRowNotFound as err:
        print(err, file=sys.stderr)
        return 1
    enricher = FimEnricher(FixtureSteckbriefSource.from_json_file(Path(args.input)), settings.fim_portal_base_url)
    return _enrich(enricher, catalogue)


def _leika_enrich(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    try:
        catalogue = catalogue_row(Path(args.catalogue_export), args.catalogue_service_id)
    except CatalogueRowNotFound as err:
        print(err, file=sys.stderr)
        return 1
    enricher = LeikaEnricher(FixtureStammtextSource.from_json_file(Path(args.input)), settings.fim_portal_base_url)
    return _enrich(enricher, catalogue)


def _fim_probe(args: argparse.Namespace) -> int:
    fetcher = PoliteUrlFetcher(user_agent=load_bot_settings().user_agent)
    results = probe_keys(fetcher, args.base_url, args.keys)
    print("\n".join(probe_lines(results)))
    return 0 if gate_passed(results) else 1


def _steckbrief_keys_arg(raw: str) -> tuple[str, ...]:
    """Parse a comma separated ``--keys`` value into 14-digit steckbrief keys."""
    keys = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not keys or not all(STECKBRIEF_KEY_PATTERN.fullmatch(key) for key in keys):
        raise argparse.ArgumentTypeError(f"expected comma separated 14-digit steckbrief keys; got {raw!r}")
    return keys


def _task_kinds_arg(raw: str) -> tuple[DiscoveryTaskKind, ...]:
    """Parse a comma separated ``--kinds`` value into known task kinds."""
    names = [name.strip() for name in raw.split(",")]
    kinds = tuple(name for name in names if is_task_kind(name))
    if not kinds or len(kinds) != len(names):
        raise argparse.ArgumentTypeError(f"expected a comma separated subset of {', '.join(TASK_KINDS)}; got {raw!r}")
    return kinds


def _drain_options(args: argparse.Namespace) -> DrainOptions:
    """Map the flags to the drain options; ``--max-tasks 0`` keeps meaning the default claim size."""
    return DrainOptions(
        kinds=args.kinds,
        max_tasks=args.max_tasks or None,
        max_batches=args.max_batches,
        time_budget_seconds=args.time_budget_seconds,
        browser_budget_seconds=args.browser_budget_seconds,
        neuron_budget=args.neuron_budget,
    )


def _worker_drain(args: argparse.Namespace) -> int:
    options = _drain_options(args)
    try:
        options.policy()
    except ValueError as err:
        print(f"invalid drain bounds: {err}", file=sys.stderr)
        return 2
    settings = load_ingest_settings()
    try:
        with DiscoveryIngestClient.from_settings(settings) as client:
            report = run_drain(options, settings, client)
    except (BrowserSetupError, LlmSetupError) as err:
        print(err, file=sys.stderr)
        return err.exit_code
    except DiscoveryMachineApiError as err:
        print(f"drain failed: {err}", file=sys.stderr)
        return 1
    print(json.dumps(report.model_dump(mode="json")))
    return 0 if report.succeeded else 1


def _candidates_emit(args: argparse.Namespace) -> int:
    selection = EmitSelection(tuple(args.id or ()), args.min_mentions, args.limit)
    try:
        selection.validate()
    except ValueError as err:
        print(f"invalid selection: {err}", file=sys.stderr)
        return 2
    settings = load_ingest_settings()
    report = preview_report if args.dry_run else emit_report
    try:
        with DiscoveryIngestClient.from_settings(settings) as client:
            lines = report(client, selection)
    except DiscoveryMachineApiError as err:
        print(f"emit failed: {err}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


def _pvog_vocabulary(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    pvog = PvogClient(settings.pvog_api_base_url)
    try:
        codes = pvog.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)
    except PvogClientError as err:
        print(err, file=sys.stderr)
        return 1
    print("\n".join(codes))
    return 0


_COMMANDS: dict[tuple[str, str | None], Callable[[argparse.Namespace], int]] = {
    ("govdata", "run"): _govdata_run,
    ("govdata", "fetch"): _govdata_fetch,
    ("pvog", "run"): _pvog_run,
    ("pvog", "vocabulary"): _pvog_vocabulary,
    ("fim", "enrich"): _fim_enrich,
    ("fim", "probe"): _fim_probe,
    ("leika", "enrich"): _leika_enrich,
    ("worker", "drain"): _worker_drain,
    ("candidates", "emit"): _candidates_emit,
    ("candidates", "page"): candidates_page,
    ("candidates", "curate"): candidates_curate,
    ("budget", "show"): budget_show,
    ("budget", "report-minutes"): budget_report_minutes,
    ("browser", "probe"): browser_probe,
    ("llm", "probe"): llm_probe,
    ("llm", "eval"): llm_eval,
    ("llm", "requeue"): llm_requeue,
    ("capture", "requeue"): capture_requeue,
    ("artifacts", "list"): artifacts_list,
    ("artifacts", "download"): artifacts_download,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="discovery_ingest")
    sub = parser.add_subparsers(dest="command")

    govdata = sub.add_parser("govdata", help="GovData OZG catalogue ingest")
    govdata_sub = govdata.add_subparsers(dest="govdata_command")
    run = govdata_sub.add_parser("run", help="Upsert rows from a Leistungen JSON export")
    run.add_argument("--input", required=True, help="Path to OZG Leistungen JSON page")
    run.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal rows (ars 000000000000)",
    )
    fetch = govdata_sub.add_parser("fetch", help="Fetch OZG Leistungen from GovData CKAN and upsert")
    fetch.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal rows (ars 000000000000)",
    )
    fetch.add_argument(
        "--max-pages",
        type=int,
        default=150,
        help="Maximum Leistungen feed pages per run (default 150)",
    )
    fetch.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Rows per Leistungen feed page (default 100)",
    )
    fetch.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional safety cap on total rows fetched",
    )

    pvog = sub.add_parser("pvog", help="PVOG Suchdienst catalogue ingest")
    pvog_sub = pvog.add_subparsers(dest="pvog_command")
    pvog_run = pvog_sub.add_parser("run", help="Upsert rows from PVOG Suchdienst API")
    pvog_run.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal scope (ars 000000000000)",
    )
    pvog_run.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on PVOG pagination pages per run",
    )
    pvog_sub.add_parser(
        "vocabulary",
        help="Print the full personalMatters leaf vocabulary from the v7 bootstrap tree",
    )

    fim = sub.add_parser("fim", help="FIM Portal enrich")
    fim_sub = fim.add_subparsers(dest="fim_command")
    fim_enrich = fim_sub.add_parser("enrich", help="Upsert entity and claims from steckbrief")
    fim_enrich.add_argument("--catalogue-service-id", type=UUID, required=True)
    fim_enrich.add_argument("--catalogue-export", required=True, help="Admin catalogue export JSON")
    fim_enrich.add_argument("--input", required=True, help="Steckbrief JSON fixture or snapshot")

    fim_probe = fim_sub.add_parser("probe", help="Report status and top-level keys of live steckbriefe")
    fim_probe.add_argument("--keys", type=_steckbrief_keys_arg, required=True, help="Comma separated 14-digit keys")
    fim_probe.add_argument("--base-url", default=DEFAULT_FIM_PORTAL_URL, help="FIM Portal base URL")

    leika = sub.add_parser("leika", help="LeiKa stammtext enrich")
    leika_sub = leika.add_subparsers(dest="leika_command")
    leika_enrich = leika_sub.add_parser("enrich", help="Upsert entity and claims from LeiKa stammtext")
    leika_enrich.add_argument("--catalogue-service-id", type=UUID, required=True)
    leika_enrich.add_argument("--catalogue-export", required=True, help="Admin catalogue export JSON")
    leika_enrich.add_argument("--input", required=True, help="Stammtext JSON fixture or snapshot")

    worker = sub.add_parser("worker", help="Discovery task worker")
    worker_sub = worker.add_subparsers(dest="worker_command")
    worker_drain = worker_sub.add_parser("drain", help="Claim tasks, fetch URLs, complete or fail")
    worker_drain.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Maximum tasks per claim request (1–50; default 50, or 5 when llm_extract is drained)",
    )
    worker_drain.add_argument(
        "--max-batches",
        type=int,
        default=1,
        help="Maximum claim/process batches (positive, default 1)",
    )
    worker_drain.add_argument(
        "--time-budget-seconds",
        type=float,
        default=None,
        help="Optional positive wall-clock budget for the whole drain",
    )
    worker_drain.add_argument(
        "--browser-budget-seconds",
        type=float,
        default=570.0,
        help="Browser seconds this run may spend on render_page and capture_screenshot (positive, default 570)",
    )
    worker_drain.add_argument(
        "--neuron-budget",
        type=float,
        default=None,
        help="Workers AI neurons this run may spend on llm_extract: it stops once the budget is reached, and the last call may pass it by its own cost (positive; required for that kind, no default)",
    )
    worker_drain.add_argument(
        "--kinds",
        type=_task_kinds_arg,
        default=WORKER_DEFAULT_TASK_KINDS,
        help="Comma separated task kinds to claim (default fetch_url,enrich_metadata,harvest_payload,extract_page; render_page and capture_screenshot need Cloudflare settings and artifact storage; llm_extract also needs the Workers AI token, LLM_MODEL, a readable ledger and --neuron-budget)",
    )

    candidates = sub.add_parser("candidates", help="Document candidates")
    candidates_sub = candidates.add_subparsers(dest="candidates_command")
    emit = candidates_sub.add_parser("emit", help="Emit staged candidates as pending suggestions")
    chosen = emit.add_mutually_exclusive_group(required=True)
    chosen.add_argument("--id", type=UUID, action="append", help="Candidate to emit (repeatable)")
    chosen.add_argument("--all-staged", action="store_true", help="Emit the most mentioned staged candidates")
    emit.add_argument("--min-mentions", type=int, default=0, help="With --all-staged: minimum mentions (default 0)")
    emit.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_EMIT_LIMIT,
        help=f"Maximum candidates to emit (1-50, default {DEFAULT_EMIT_LIMIT})",
    )
    emit.add_argument("--dry-run", action="store_true", help="Preview only; nothing is written")
    register_candidates_aids(candidates_sub)
    register_budget_parser(sub)
    register_browser_parser(sub)
    register_llm_parser(sub)
    register_artifacts_parser(sub)
    register_capture_parser(sub)
    return parser
