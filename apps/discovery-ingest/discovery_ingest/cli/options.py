"""Shared option types and value parsers for the ingest CLI.

A parser that rejects a value raises ``typer.BadParameter``, which exits 2 as argparse's ``type=`` errors did.
"""

from __future__ import annotations

from typing import Annotated

import typer

from discovery_ingest.browser.probe_plan import VARIANTS
from discovery_ingest.budget_models import BUDGET_RESOURCES, BudgetResource, is_budget_resource
from discovery_ingest.fim.keys import STECKBRIEF_KEY_PATTERN
from discovery_ingest.operations.budget import Requirement
from discovery_ingest.operations.requeue import DEFAULT_LIMIT, MAX_LIMIT
from discovery_ingest.schemas import TASK_KINDS, DiscoveryTaskKind, is_task_kind


def positive_int(raw: str | int) -> int:
    """Parse a whole number of at least 1; click also passes integer defaults through here."""
    text = str(raw)
    if not text.isdigit() or int(text) < 1:
        raise typer.BadParameter(f"expected a positive whole number; got {text!r}")
    return int(text)


def positive_minutes(raw: str) -> int:
    """Parse a whole number of minutes of at least 1."""
    if not raw.isdigit() or int(raw) < 1:
        raise typer.BadParameter(f"expected a positive whole number of minutes; got {raw!r}")
    return int(raw)


def requeue_limit(raw: str | int) -> int:
    """Parse ``--limit`` of a requeue: a whole number from 1 to :data:`MAX_LIMIT`."""
    text = str(raw)
    if not text.isdigit() or not 1 <= int(text) <= MAX_LIMIT:
        raise typer.BadParameter(f"expected a whole number from 1 to {MAX_LIMIT}; got {text!r}")
    return int(text)


def steckbrief_keys(raw: str) -> tuple[str, ...]:
    """Parse a comma separated ``--keys`` value into 14-digit steckbrief keys."""
    keys = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not keys or not all(STECKBRIEF_KEY_PATTERN.fullmatch(key) for key in keys):
        raise typer.BadParameter(f"expected comma separated 14-digit steckbrief keys; got {raw!r}")
    return keys


def task_kinds(raw: str) -> tuple[DiscoveryTaskKind, ...]:
    """Parse a comma separated ``--kinds`` value into known task kinds."""
    names = [name.strip() for name in raw.split(",")]
    kinds = tuple(name for name in names if is_task_kind(name))
    if not kinds or len(kinds) != len(names):
        raise typer.BadParameter(f"expected a comma separated subset of {', '.join(TASK_KINDS)}; got {raw!r}")
    return kinds


def budget_resource(raw: str) -> BudgetResource:
    """Parse a ledger resource name."""
    if not is_budget_resource(raw):
        raise typer.BadParameter(f"expected one of {', '.join(BUDGET_RESOURCES)}; got {raw!r}")
    return raw


def budget_requirement(raw: str) -> Requirement:
    """Parse ``RESOURCE=N`` into a resource and a non-negative amount."""
    name, _, amount = raw.partition("=")
    try:
        needed = float(amount)
    except ValueError:
        needed = -1.0
    if needed < 0:
        raise typer.BadParameter(f"expected RESOURCE=N with N >= 0; got {raw!r}")
    return budget_resource(name), needed


def probe_variant(raw: str) -> str:
    """Parse a browser probe variant name."""
    if raw not in VARIANTS:
        raise typer.BadParameter(f"expected one of {', '.join(VARIANTS)}; got {raw!r}")
    return raw


RequeueHost = Annotated[
    str | None,
    typer.Option("--host", help="Only pages of this source host (default: every host)"),
]
RequeueLimit = Annotated[
    int,
    typer.Option(
        "--limit",
        parser=requeue_limit,
        help=f"Maximum pages to queue (1-{MAX_LIMIT}, default {DEFAULT_LIMIT})",
    ),
]
RequeueDryRun = Annotated[bool, typer.Option("--dry-run", help="Count the pages; make no enqueue call")]
