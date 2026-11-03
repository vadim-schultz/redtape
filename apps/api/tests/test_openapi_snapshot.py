"""The committed OpenAPI snapshot the web contract test reads must match the API."""

from __future__ import annotations

from pathlib import Path

from scripts.export_openapi import REGENERATE_COMMAND, SNAPSHOT_PATH, snapshot_problem


def test_matches_the_committed_file() -> None:
    assert snapshot_problem(SNAPSHOT_PATH) is None


def test_fails_with_the_regenerate_command_when_stale(tmp_path: Path) -> None:
    stale = tmp_path / "openapi.schemas.json"
    stale.write_text("{}\n", encoding="utf-8")

    problem = snapshot_problem(stale)

    assert problem is not None
    assert problem.startswith("stale")
    assert REGENERATE_COMMAND in problem
