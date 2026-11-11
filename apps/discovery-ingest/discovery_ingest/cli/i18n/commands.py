"""``i18n translate-ui``: translate the interface strings and category labels of one locale."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, fail
from discovery_ingest.cli.i18n.app import i18n_app
from discovery_ingest.i18n.locales import UI_TARGET_LOCALES
from discovery_ingest.i18n.translate_ui import BATCH_SIZE, UiReport
from discovery_ingest.operations.translate_ui import DEFAULT_NEURON_BUDGET, TranslateUiRequest, run_translate_ui
from discovery_ingest.translation.meter import NoMeterForUnitError
from discovery_ingest.translation.settings import TranslationSettings, load_translation_settings
from discovery_ingest.worker.llm_setup import LlmSetupError

EXIT_INCOMPLETE = 3
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[5]


def _settings() -> TranslationSettings:
    try:
        return load_translation_settings()
    except ValidationError as err:
        fail(f"invalid translation settings: {err}", EXIT_USAGE)


def _request(locale: str, repo_root: Path, batch_size: int, neuron_budget: float) -> TranslateUiRequest:
    """Return the request, or exit 2 for a locale that is not a UI target, a bound out of range or a missing checkout."""
    if locale not in UI_TARGET_LOCALES:
        fail(f"--locale must be one of: {', '.join(UI_TARGET_LOCALES)}", EXIT_USAGE)
    if batch_size < 1 or neuron_budget < 1:
        fail("--batch-size and --neuron-budget must be at least 1", EXIT_USAGE)
    if not (repo_root / "apps" / "api" / "scripts" / "seed_data" / "translations" / "en.json").is_file():
        fail(f"{repo_root} is not a redtape checkout (no English seed file); pass --repo-root", EXIT_USAGE)
    return TranslateUiRequest(locale, repo_root, batch_size, neuron_budget)


def _exit_code(report: UiReport) -> int:
    if report.stopped:
        return EXIT_INCOMPLETE
    return EXIT_FAILED if report.rejected or report.gaps else 0


@i18n_app.command("translate-ui")
def translate_ui(
    ctx: typer.Context,
    locale: Annotated[str, typer.Option("--locale", help="Target locale: tr, ru, uk, pl or ro")],
    repo_root: Annotated[
        Path | None, typer.Option("--repo-root", help="The redtape checkout to read and write (default: this one)")
    ] = None,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Strings per model call")] = BATCH_SIZE,
    neuron_budget: Annotated[
        float,
        typer.Option(
            "--neuron-budget",
            help="Neurons this run may spend; it never takes the day's ledger below QUERY_EMBED_RESERVE",
        ),
    ] = DEFAULT_NEURON_BUDGET,
) -> None:
    """Translate the interface strings and category labels the locale lacks; a rerun continues where this one stopped.

    Writes the API seed file, its web mirror, the taxonomy module and review.json (status machine). Exit 3 when the
    run stopped early (quota, budget), 1 when strings were rejected, 0 otherwise.
    """
    request = _request(locale, repo_root or DEFAULT_REPO_ROOT, batch_size, neuron_budget)
    try:
        outcome = run_translate_ui(request, _settings(), api_client(ctx))
    except LlmSetupError as err:
        fail(str(err), err.exit_code)
    except NoMeterForUnitError as err:
        fail(str(err), EXIT_USAGE)
    typer.echo(json.dumps(outcome.as_json(), ensure_ascii=False))
    if code := _exit_code(outcome.report):
        raise typer.Exit(code)
