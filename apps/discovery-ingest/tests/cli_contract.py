"""The command line contract of ``python -m discovery_ingest``: the 26 commands as data.

Every row is a fact the workflows in ``.github/workflows`` and the operator docs rely on: command names,
flags, value kinds, defaults, choices and repeatability. The adapters in ``cli_adapters.py`` read the real
CLI and are compared against these rows, so a migration that changes a row fails the contract tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

import discovery_ingest
from discovery_ingest.artifacts import ArtifactKind
from discovery_ingest.candidate_emit import DEFAULT_EMIT_LIMIT
from discovery_ingest.config import DEFAULT_FIM_PORTAL_URL
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION
from discovery_ingest.schemas import WORKER_DEFAULT_TASK_KINDS

GROUPS = (
    "govdata",
    "pvog",
    "fim",
    "leika",
    "worker",
    "candidates",
    "budget",
    "browser",
    "llm",
    "artifacts",
    "capture",
    "embed",
    "translate",
)

DEFAULT_GOLD_DIR = Path(discovery_ingest.__file__).resolve().parents[1] / "tests" / "fixtures" / "gold"
"""The gold directory ``llm eval`` reads when ``--gold-dir`` is not given."""


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """One option of a command: its flags, the kind of its value and its defaults."""

    flags: tuple[str, ...]
    kind: str
    required: bool = False
    default: object = None
    choices: tuple[str, ...] | None = None
    repeatable: bool = False


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """One ``<group> <command>`` pair and its options."""

    group: str
    name: str
    options: tuple[OptionSpec, ...] = field(default=())

    @property
    def path(self) -> tuple[str, str]:
        """Return the ``(group, command)`` pair that names the command on the command line."""
        return (self.group, self.name)


def _opt(flags: str, kind: str, **kwargs: object) -> OptionSpec:
    if kind == FLAG:
        kwargs.setdefault("default", False)
    return OptionSpec(tuple(flags.split()), kind, **kwargs)


FLAG = "flag"
UUID_REQUIRED = _opt("--jurisdiction-id", "uuid", required=True)

COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec("govdata", "run", (_opt("--input", "str", required=True), UUID_REQUIRED)),
    CommandSpec(
        "govdata",
        "fetch",
        (
            UUID_REQUIRED,
            _opt("--max-pages", "int", default=150),
            _opt("--page-size", "int", default=100),
            _opt("--max-records", "int"),
        ),
    ),
    CommandSpec("pvog", "run", (UUID_REQUIRED, _opt("--max-pages", "int"))),
    CommandSpec("pvog", "vocabulary"),
    CommandSpec(
        "fim",
        "enrich",
        (
            _opt("--catalogue-service-id", "uuid", required=True),
            _opt("--catalogue-export", "str", required=True),
            _opt("--input", "str", required=True),
        ),
    ),
    CommandSpec(
        "fim",
        "probe",
        (_opt("--keys", "str", required=True), _opt("--base-url", "str", default=DEFAULT_FIM_PORTAL_URL)),
    ),
    CommandSpec(
        "leika",
        "enrich",
        (
            _opt("--catalogue-service-id", "uuid", required=True),
            _opt("--catalogue-export", "str", required=True),
            _opt("--input", "str", required=True),
        ),
    ),
    CommandSpec(
        "worker",
        "drain",
        (
            _opt("--max-tasks", "int"),
            _opt("--max-batches", "int", default=1),
            _opt("--time-budget-seconds", "float"),
            _opt("--browser-budget-seconds", "float", default=570.0),
            _opt("--neuron-budget", "float"),
            _opt("--kinds", "str", default=",".join(WORKER_DEFAULT_TASK_KINDS)),
        ),
    ),
    CommandSpec(
        "candidates",
        "emit",
        (
            _opt("--id", "uuid", repeatable=True),
            _opt("--all-staged", FLAG),
            _opt("--min-mentions", "int", default=0),
            _opt("--limit", "int", default=DEFAULT_EMIT_LIMIT),
            _opt("--dry-run", FLAG),
        ),
    ),
    CommandSpec(
        "candidates",
        "page",
        (_opt("--candidate-id", "uuid", required=True), _opt("--out", "path")),
    ),
    CommandSpec(
        "candidates",
        "curate",
        (
            _opt("--file", "str", required=True),
            _opt("--dry-run", FLAG),
            _opt("--check-pages --no-check-pages", "bool-optional", default=True),
        ),
    ),
    CommandSpec(
        "budget",
        "show",
        (
            _opt("--resource", "str", repeatable=True),
            _opt("--require-remaining", "str", repeatable=True),
            _opt("--strict", FLAG),
        ),
    ),
    CommandSpec("budget", "report-minutes", (_opt("--minutes", "custom", required=True),)),
    CommandSpec(
        "browser",
        "probe",
        (
            _opt("--url", "str", repeatable=True),
            _opt("--error-url", "str", repeatable=True),
            _opt("--variant", "custom", repeatable=True),
            _opt("--max-browser-seconds", "float", default=240.0),
        ),
    ),
    CommandSpec(
        "llm",
        "eval",
        (
            _opt("--model", "str", required=True),
            _opt("--prompt-version", "str", default=PROMPT_VERSION),
            _opt("--limit", "int"),
            _opt("--out", "str"),
            _opt("--neuron-budget", "float", default=4000.0),
            _opt("--gold-dir", "str", default=str(DEFAULT_GOLD_DIR)),
            _opt("--cache-dir", "str", default=".llm-eval-cache"),
        ),
    ),
    CommandSpec(
        "llm",
        "requeue",
        (_opt("--host", "str"), _opt("--limit", "custom", default=50), _opt("--dry-run", FLAG)),
    ),
    CommandSpec(
        "llm",
        "probe",
        (
            _opt("--model", "str", repeatable=True),
            _opt("--fixture", "str", required=True),
            _opt("--max-neurons", "float", default=900.0),
        ),
    ),
    CommandSpec(
        "artifacts",
        "list",
        (
            _opt("--host", "str", required=True),
            _opt("--limit", "custom", default=20),
            _opt("--kind", "str", default="html_snapshot", choices=tuple(get_args(ArtifactKind))),
        ),
    ),
    CommandSpec("artifacts", "download", (_opt("--id", "uuid", required=True), _opt("--out", "path", required=True))),
    CommandSpec(
        "capture",
        "requeue",
        (
            _opt("--host", "str"),
            _opt("--limit", "custom", default=50),
            _opt("--dry-run", FLAG),
            _opt("--service-id", "uuid", repeatable=True),
        ),
    ),
    CommandSpec("embed", "probe", (_opt("--model", "str"),)),
    CommandSpec(
        "embed",
        "drain",
        (
            _opt("--max-tasks", "int", default=50),
            _opt("--max-batches", "int", default=1),
            _opt("--time-budget-seconds", "float"),
            _opt("--neuron-budget", "float", default=3000.0),
        ),
    ),
    CommandSpec("embed", "summary", (_opt("--require-pending", FLAG),)),
    CommandSpec(
        "translate",
        "probe",
        (
            _opt("--locale", "str", required=True),
            _opt("--sample", "int", default=50),
            _opt("--engine", "str"),
            _opt("--model", "str"),
            _opt("--sheet", "path"),
            _opt("--max-usage", "float", default=3000.0),
            _opt("--daily-budget", "float", default=9500.0),
        ),
    ),
    CommandSpec(
        "translate",
        "drain",
        (
            _opt("--max-tasks", "int", default=10),
            _opt("--max-batches", "int", default=1),
            _opt("--time-budget-seconds", "float"),
            _opt("--neuron-budget", "float", default=2500.0),
        ),
    ),
    CommandSpec("translate", "summary", (_opt("--require-pending", FLAG),)),
)

assert len(COMMANDS) == 26, "the contract documents exactly twenty-six commands"
assert {spec.group for spec in COMMANDS} == set(GROUPS)
