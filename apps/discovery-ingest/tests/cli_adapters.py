"""Adapters that describe the live CLI in the terms of ``cli_contract.py``.

The adapter walks the Typer app's click command tree (``typer.main.get_command``). Parsing is checked
without running a command: ``accepts`` builds the click context of the leaf command and stops there.
"""

from __future__ import annotations

from typing import Any

import typer
from discovery_ingest.cli import app
from discovery_ingest.cli.options import task_kinds
from discovery_ingest.operations.drain import DrainOptions
from typer.main import get_command

from cli_contract import CommandSpec, OptionSpec

PROG_NAME = "discovery_ingest"
_KIND_BY_TYPE = {"str": "str", "int": "int", "float": "float", "uuid": "uuid", "path": "path"}


def _root() -> Any:
    return get_command(app)


def _kind(param: Any) -> str:
    if param.is_flag:
        return "bool-optional" if param.secondary_opts else "flag"
    if param.type.name == "choice":
        return "str"
    return _KIND_BY_TYPE.get(param.type.name, "custom")


def _default(param: Any) -> object:
    value = param.default
    if isinstance(value, (list, tuple)):
        return tuple(value) if value else None
    return value


def _option(param: Any) -> OptionSpec:
    choices = tuple(param.type.choices) if param.type.name == "choice" else None
    return OptionSpec(
        flags=tuple([*param.opts, *param.secondary_opts]),
        kind=_kind(param),
        required=bool(param.required),
        default=_default(param),
        choices=choices,
        repeatable=bool(param.multiple),
    )


def describe() -> list[CommandSpec]:
    """Return every ``<group> <command>`` pair of the live CLI with its options, in registration order."""
    specs: list[CommandSpec] = []
    for group_name, group in _root().commands.items():
        for name, command in group.commands.items():
            options = tuple(_option(param) for param in command.params if param.opts)
            specs.append(CommandSpec(group_name, name, options))
    return specs


def groups() -> list[str]:
    """Return the group names in registration order."""
    return list(_root().commands)


def _leaf(argv: list[str]) -> tuple[Any, str, list[str]]:
    """Resolve the leaf command of ``argv``; return it with its name and the tokens after it (no command runs)."""
    command = _root()
    name, tokens = PROG_NAME, list(argv)
    while getattr(command, "commands", None) is not None:
        if not tokens or tokens[0] not in command.commands:
            raise LookupError(f"no command {' '.join(argv)}")
        name = tokens.pop(0)
        command = command.commands[name]
    return command, name, tokens


def accepts(argv: list[str]) -> bool:
    """Return whether the CLI accepts ``argv`` (group, command and options) without running the command."""
    try:
        command, name, tokens = _leaf(argv)
        command.make_context(name, tokens)
    except (LookupError, typer.exceptions.TyperException, typer.Exit, SystemExit):
        return False
    return True


def parsed_params(argv: list[str]) -> dict[str, Any]:
    """Return the values click parses for the leaf command of ``argv``, keyed by parameter name."""
    command, name, tokens = _leaf(argv)
    return dict(command.make_context(name, tokens).params)


def drain_options(argv: list[str]) -> DrainOptions:
    """Return the drain options the ``worker drain`` command builds from ``argv`` (the mapping the command uses)."""
    params = parsed_params(argv)
    return DrainOptions(
        kinds=task_kinds(params["kinds"]),
        max_tasks=params["max_tasks"] or None,
        max_batches=params["max_batches"],
        time_budget_seconds=params["time_budget_seconds"],
        browser_budget_seconds=params["browser_budget_seconds"],
        neuron_budget=params["neuron_budget"],
    )
