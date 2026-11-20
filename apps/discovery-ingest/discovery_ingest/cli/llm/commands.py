"""``llm``: Cloudflare Workers AI: ``eval`` on the gold set, ``requeue`` of extraction tasks, and ``probe`` of models."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import (
    EXIT_FAILED,
    EXIT_USAGE,
    HELP_OPTIONS,
    fail,
    handles_api_errors,
    show_help_without_subcommand,
)
from discovery_ingest.cli.options import RequeueDryRun, RequeueHost, RequeueLimit
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION
from discovery_ingest.llm_settings import load_llm_settings
from discovery_ingest.operations.eval import (
    DEFAULT_CACHE_DIR,
    DEFAULT_GOLD_DIR,
    DEFAULT_NEURON_BUDGET,
    EvalOptions,
    EvalRefused,
    run_eval,
    startup_problem,
)
from discovery_ingest.operations.probes import llm_probe
from discovery_ingest.operations.requeue import DEFAULT_LIMIT, Counts, llm_requeue, llm_superseded_requeue
from discovery_ingest.schemas import TaskSupersededResponse
from discovery_ingest.worker.llm_enqueue import llm_input_key

EXIT_MISSING_MODEL = 2
DEFAULT_MAX_NEURONS = 900.0
StaleOnly = Annotated[
    bool,
    typer.Option(
        "--stale-only",
        help="Re-pend the extractions made under an older key, once per page (no --host: the selection spans hosts)",
    ),
]

llm_app = typer.Typer(
    name="llm",
    help="Cloudflare Workers AI",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@llm_app.callback(invoke_without_command=True)
def llm_group(ctx: typer.Context) -> None:
    """Cloudflare Workers AI."""
    show_help_without_subcommand(ctx)


@llm_app.command("eval")
def llm_eval(
    ctx: typer.Context,
    model: Annotated[str, typer.Option("--model", help="A Workers AI model id with a price row")],
    prompt_version: Annotated[
        str, typer.Option("--prompt-version", help=f"The prompt version (default {PROMPT_VERSION})")
    ] = PROMPT_VERSION,
    limit: Annotated[int | None, typer.Option("--limit", help="Only the first N gold pages by name")] = None,
    out: Annotated[str | None, typer.Option("--out", help="Write the per-page results as JSON to this file")] = None,
    neuron_budget: Annotated[
        float,
        typer.Option(
            "--neuron-budget",
            help=(
                "Stop once this many neurons are used; the last call may pass it by its own cost "
                f"(default {DEFAULT_NEURON_BUDGET:g})"
            ),
        ),
    ] = DEFAULT_NEURON_BUDGET,
    gold_dir: Annotated[str, typer.Option("--gold-dir", help="Directory of the gold pages and labels")] = str(
        DEFAULT_GOLD_DIR
    ),
    cache_dir: Annotated[str, typer.Option("--cache-dir", help="Directory of cached model answers")] = str(
        DEFAULT_CACHE_DIR
    ),
) -> None:
    """Measure a model on the gold set and print a table."""
    try:
        settings = settings_of(ctx)
    except ValidationError as err:
        fail(f"missing environment: {', '.join(str(e['loc'][0]) for e in err.errors())}", EXIT_USAGE)
    options = EvalOptions(
        model=model,
        prompt_version=prompt_version,
        limit=limit,
        out=out,
        neuron_budget=neuron_budget,
        gold_dir=gold_dir,
        cache_dir=cache_dir,
    )
    if problem := startup_problem(options, settings):
        fail(problem, EXIT_USAGE)
    try:
        result = run_eval(settings, options)
    except EvalRefused as err:
        fail(err.message, err.code)
    typer.echo("\n".join(result.lines))
    if result.stopped:
        raise typer.Exit(EXIT_FAILED)


def _requeue_report(model: str, counts: Counts, *, dry_run: bool) -> str:
    fields = [f"key={llm_input_key(model)}", f"pages={counts.pages}", f"queued={counts.queued}"]
    fields += [f"already_queued={counts.already_queued}", f"failed={counts.failed}"]
    return " ".join([*fields, "dry_run=true"] if dry_run else fields)


def _superseded_report(model: str, result: TaskSupersededResponse, *, dry_run: bool) -> str:
    return (
        f"key={llm_input_key(model)} matched={result.matched} requeued={result.requeued} dry_run={str(dry_run).lower()}"
    )


def _requeue_superseded(ctx: typer.Context, host: str | None, limit: int, dry_run: bool, model: str) -> None:
    if host is not None:
        fail("--host does not combine with --stale-only: the superseded requeue selects across hosts", EXIT_USAGE)
    result = llm_superseded_requeue(api_client(ctx), limit=limit, model=model, dry_run=dry_run)
    typer.echo(_superseded_report(model, result, dry_run=dry_run))


@llm_app.command("requeue")
@handles_api_errors("llm requeue")
def llm_requeue_command(
    ctx: typer.Context,
    host: RequeueHost = None,
    limit: RequeueLimit = DEFAULT_LIMIT,
    dry_run: RequeueDryRun = False,
    stale_only: StaleOnly = False,
) -> None:
    """Queue llm_extract for the latest snapshots under the current key; --stale-only re-pends the older extractions."""
    settings = settings_of(ctx)
    if not settings.llm_model:
        fail("llm requeue needs the environment variable LLM_MODEL (it keys the task)", EXIT_MISSING_MODEL)
    if stale_only:
        _requeue_superseded(ctx, host, limit, dry_run, settings.llm_model)
        return
    counts = llm_requeue(api_client(ctx), host=host, limit=limit, model=settings.llm_model, dry_run=dry_run)
    typer.echo(_requeue_report(settings.llm_model, counts, dry_run=dry_run))
    if counts.failed:
        raise typer.Exit(EXIT_FAILED)


@llm_app.command("probe")
def llm_probe_command(
    fixture: Annotated[str, typer.Option("--fixture", help="Path of a rendered HTML page to clean and send")],
    model: Annotated[list[str] | None, typer.Option("--model", help="A Workers AI model id (repeatable)")] = None,
    max_neurons: Annotated[
        float,
        typer.Option(
            "--max-neurons",
            help=(
                "Stop before the next model once this many neurons are computed spent "
                f"(default {DEFAULT_MAX_NEURONS:g})"
            ),
        ),
    ] = DEFAULT_MAX_NEURONS,
) -> None:
    """Probe models on one fixture and print a table."""
    settings = load_llm_settings()
    if settings.missing_ai_credentials():
        fail(f"missing environment: {', '.join(settings.missing_ai_credentials())}", EXIT_USAGE)
    path = Path(fixture)
    models = model or [settings.llm_model or ""]
    if not path.is_file():
        fail(f"fixture not found: {path}", EXIT_USAGE)
    if not all(models):
        fail("no model: pass --model <id> (repeatable) or set LLM_MODEL", EXIT_USAGE)
    outcome = llm_probe(settings, models=models, fixture=path, max_neurons=max_neurons)
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)
