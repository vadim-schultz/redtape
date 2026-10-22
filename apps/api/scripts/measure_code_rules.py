"""Report class sizes, method sizes, and parameter counts for a source tree.

Informational: prints a per-unit table and totals, and exits 0 unless a file
cannot be parsed.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

CLASS_LIMIT = 100
METHOD_LIMIT = 5
PARAM_LIMIT = 3


class MeasureError(Exception):
    """Raised when a source file cannot be parsed."""


@dataclass(frozen=True)
class ClassSize:
    """Line count of one class."""

    path: Path
    name: str
    lines: int


@dataclass(frozen=True)
class MethodSize:
    """Line and parameter count of one function or method."""

    path: Path
    name: str
    lines: int
    parameters: int


@dataclass(frozen=True)
class FileReport:
    """Measured classes and methods of one file."""

    classes: list[ClassSize] = field(default_factory=list)
    methods: list[MethodSize] = field(default_factory=list)


@dataclass(frozen=True)
class Summary:
    """Counts of units over the limits."""

    classes_over: int
    methods_over: int
    params_over: int


def _span(node: ast.AST) -> int:
    """Return the number of source lines a node covers."""
    return int(getattr(node, "end_lineno", 0)) - int(getattr(node, "lineno", 0)) + 1


def _parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count parameters, ignoring self and cls."""
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    extra = int(args.vararg is not None) + int(args.kwarg is not None)
    return len([n for n in names if n not in {"self", "cls"}]) + extra


def measure_file(path: Path) -> FileReport:
    """Measure every class and function in one file."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as err:
        raise MeasureError(f"cannot parse {path}: {err}") from err
    classes = [ClassSize(path, n.name, _span(n)) for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    methods = [MethodSize(path, n.name, _span(n), _parameter_count(n)) for n in funcs]
    return FileReport(classes, methods)


def summarise(reports: Iterable[FileReport], *, class_limit: int, method_limit: int, param_limit: int) -> Summary:
    """Count units over the given limits."""
    reps = list(reports)
    return Summary(
        classes_over=sum(c.lines > class_limit for r in reps for c in r.classes),
        methods_over=sum(m.lines > method_limit for r in reps for m in r.methods),
        params_over=sum(m.parameters > param_limit for r in reps for m in r.methods),
    )


def _print_offenders(reports: Sequence[FileReport]) -> None:
    """Print each unit that is over a limit."""
    for report in reports:
        for c in report.classes:
            if c.lines > CLASS_LIMIT:
                print(f"class  {c.lines:4d} lines  {c.path}:{c.name}")
        for m in report.methods:
            if m.lines > METHOD_LIMIT or m.parameters > PARAM_LIMIT:
                print(f"method {m.lines:4d} lines {m.parameters} params  {m.path}:{m.name}")


def main(argv: Sequence[str]) -> int:
    """Measure the given roots (default: app) and print offenders and totals."""
    roots = [Path(a) for a in argv] or [Path("app")]
    reports = [measure_file(p) for root in roots for p in sorted(root.rglob("*.py"))]
    _print_offenders(reports)
    s = summarise(reports, class_limit=CLASS_LIMIT, method_limit=METHOD_LIMIT, param_limit=PARAM_LIMIT)
    print(
        f"classes>{CLASS_LIMIT}: {s.classes_over}  methods>{METHOD_LIMIT}: {s.methods_over}  params>{PARAM_LIMIT}: {s.params_over}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
