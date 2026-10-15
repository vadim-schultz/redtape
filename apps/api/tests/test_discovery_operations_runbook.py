"""Discovery layer operations runbook checks (chapter 22)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"

_MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def _relative_markdown_targets(markdown: str) -> list[str]:
    targets: list[str] = []
    for raw in _MARKDOWN_LINK.findall(markdown):
        target = raw.strip()
        if not target or target.startswith("#"):
            continue
        if "://" in target:
            continue
        path_part = target.split("#", 1)[0]
        if path_part:
            targets.append(path_part)
    return targets


def test_runbook_documents_discovery_admin_emails() -> None:
    """Runbook contains DISCOVERY_ADMIN_EMAILS."""
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "DISCOVERY_ADMIN_EMAILS" in text


def test_runbook_documents_admin_tasks_route() -> None:
    """Runbook links to /admin/discovery/tasks."""
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "/admin/discovery/tasks" in text


def test_runbook_relative_links_resolve() -> None:
    """Relative links from runbook resolve to existing files."""
    assert RUNBOOK.is_file(), f"missing runbook: {RUNBOOK.relative_to(REPO_ROOT)}"
    text = RUNBOOK.read_text(encoding="utf-8")
    base = RUNBOOK.parent
    missing: list[str] = []
    for rel in _relative_markdown_targets(text):
        resolved = (base / rel).resolve()
        if not resolved.is_file():
            missing.append(rel)
    assert not missing, f"broken relative links in runbook: {missing}"
