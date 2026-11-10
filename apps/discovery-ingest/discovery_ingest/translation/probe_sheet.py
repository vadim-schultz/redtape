"""The spot-check sheet: German and translation side by side, one row per field, with the findings and a reviewer column."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("key", "field", "german", "translation", "findings", "reviewer_note")


@dataclass(frozen=True, slots=True)
class SheetRow:
    """One field of one unit: the German text, its translation (empty when none came back) and the checks it failed."""

    key: str
    field: str
    german: str
    translation: str
    findings: str


def write_sheet(rows: list[SheetRow], path: Path) -> Path:
    """Write ``rows`` as UTF-8 CSV to ``path`` (parent directories are created) and return ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows((row.key, row.field, row.german, row.translation, row.findings, "") for row in rows)
    return path
