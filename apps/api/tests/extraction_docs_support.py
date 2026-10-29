"""Shared paths and readers for the extraction documentation contract tests (chapter E9)."""

from __future__ import annotations

import re
from pathlib import Path

from tests.crawlers_docs_support import (
    DEPLOYMENT_CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    INGEST_README,
    OPS,
    PLANS_README,
    REPO_ROOT,
    SCHEDULED_JOBS,
    WORKFLOWS,
    read,
)

__all__ = [
    "CHECKLIST",
    "DEPLOYMENT_CHECKLIST",
    "DISCOVERY_LAYER",
    "DISCOVERY_ONLINE",
    "GOLD_README",
    "INGEST",
    "INGEST_README",
    "LOOP_DOC",
    "OPS",
    "PLAN",
    "PLANS_README",
    "REPO_ROOT",
    "SCHEDULED_JOBS",
    "WORKFLOWS",
    "EXTRACTION_DOCS",
    "constant",
    "missing",
    "read",
    "squashed",
]

PLAN = REPO_ROOT / ".plans/extraction"
LOOP_DOC = OPS / "loops/extraction.md"
CHECKLIST = OPS / "extraction-operator-checklist.md"
INGEST = REPO_ROOT / "apps/discovery-ingest"
GOLD_README = INGEST / "tests/fixtures/gold/README.md"

EXTRACTION_DOCS = (
    LOOP_DOC,
    CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    SCHEDULED_JOBS,
    DEPLOYMENT_CHECKLIST,
    INGEST_README,
)


def constant(relative_path: str, name: str) -> str:
    """Return the value of the string or number constant ``name`` in an ingest source file, without importing it."""
    source = read(INGEST / relative_path)
    match = re.search(rf"^{name}\s*(?::[^=]+)?=\s*[\"']?([\w.\-]+)[\"']?", source, re.M)
    assert match, f"{name} not found in {relative_path}"
    return match.group(1).replace("_", "")


def squashed(path: Path) -> str:
    """Return the text of ``path`` with every whitespace run as one space, so a term may span a line wrap."""
    return " ".join(read(path).split())


def missing(path: Path, terms: tuple[str, ...]) -> list[str]:
    """Return the ``terms`` that ``path`` does not contain, ignoring line wraps."""
    text = squashed(path)
    return [term for term in terms if " ".join(term.split()) not in text]
