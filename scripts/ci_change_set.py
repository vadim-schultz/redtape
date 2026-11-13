#!/usr/bin/env python3
"""Decide whether a change set needs the migration round trip.

Reads the changed paths on stdin, one per line (from `git diff --name-only`),
and writes `migrations=true` or `migrations=false` to `$GITHUB_OUTPUT`, or to
stdout when that variable is unset.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable

MIGRATION_DIR = "apps/api/alembic/"
CHECK_SCRIPT = "apps/api/scripts/check_migrations.sh"


def is_migration_path(path: str) -> bool:
    return path.startswith(MIGRATION_DIR) or path == CHECK_SCRIPT


def migrations_changed(paths: Iterable[str]) -> bool:
    return any(is_migration_path(path) for path in paths)


def output_line(changed: bool) -> str:
    return f"migrations={'true' if changed else 'false'}"


def emit(line: str, target: str | None) -> None:
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    else:
        print(line)


def main() -> int:
    paths = [line.strip() for line in sys.stdin if line.strip()]
    emit(output_line(migrations_changed(paths)), os.environ.get("GITHUB_OUTPUT"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
