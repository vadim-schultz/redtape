"""Adapters that describe the live CLI in the terms of ``cli_contract.py``.

The argparse adapter walks ``_build_parser()``. It is the only adapter until the Typer migration adds the click
adapter, which then replaces this one.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from discovery_ingest.cli import _build_parser

from cli_contract import CommandSpec, OptionSpec


def _kind(action: argparse.Action) -> str:
    if isinstance(action, argparse.BooleanOptionalAction):
        return "bool-optional"
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):  # noqa: SLF001
        return "flag"
    if action.type is UUID:
        return "uuid"
    if action.type is int:
        return "int"
    if action.type is float:
        return "float"
    if action.type is Path:
        return "path"
    if action.type is None:
        return "str"
    return "custom"


def _repeatable(action: argparse.Action) -> bool:
    return isinstance(action, argparse._AppendAction) or type(action).__name__ == "_ServiceIds"  # noqa: SLF001


def _default(action: argparse.Action) -> object:
    value = action.default
    if isinstance(value, list) and not value:
        return None
    if isinstance(value, list):
        return tuple(value)
    return value


def _option(action: argparse.Action) -> OptionSpec:
    return OptionSpec(
        flags=tuple(action.option_strings),
        kind=_kind(action),
        required=bool(action.required),
        default=_default(action),
        choices=tuple(action.choices) if action.choices is not None else None,
        repeatable=_repeatable(action),
    )


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction[argparse.ArgumentParser]:  # noqa: SLF001
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action
    raise AssertionError("parser has no subcommands")


def describe() -> list[CommandSpec]:
    """Return every ``<group> <command>`` pair of the live CLI with its options, in parser order."""
    specs: list[CommandSpec] = []
    root = _build_parser()
    for group, group_parser in _subparsers(root).choices.items():
        for name, command_parser in _subparsers(group_parser).choices.items():
            options = tuple(
                _option(action)
                for action in command_parser._actions  # noqa: SLF001
                if action.option_strings and action.dest != "help"
            )
            specs.append(CommandSpec(group, name, options))
    return specs


def groups() -> list[str]:
    """Return the group names in parser order."""
    return list(_subparsers(_build_parser()).choices)


def accepts(argv: list[str]) -> bool:
    """Return whether the parser accepts ``argv`` (group, command and options) without running the command."""
    try:
        _build_parser().parse_args(argv)
    except SystemExit:
        return False
    return True
