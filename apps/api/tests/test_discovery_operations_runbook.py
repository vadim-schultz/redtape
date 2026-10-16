"""Discovery layer operations runbook checks (chapter 22)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"
DISCOVERY_ONLINE_RUNBOOK = REPO_ROOT / "docs/operations/discovery-online.md"

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


def test_runbook_discovery_api_url_documents_host_root() -> None:
    """DISCOVERY_API_URL documents host root."""
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "host root" in text
    assert "DISCOVERY_API_URL=http://localhost:8000" in text
    assert "/api/v1/discovery/machine" in text
    assert "DISCOVERY_API_URL=http://localhost:8000/api/v1/discovery/machine" not in text


def test_runbook_discovery_api_url_examples_avoid_path_doubling() -> None:
    """DISCOVERY_API_URL examples must not include the machine API path suffix."""
    text = RUNBOOK.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "DISCOVERY_API_URL=" not in line:
            continue
        _, _, value = line.partition("DISCOVERY_API_URL=")
        value = value.strip().strip("`")
        if not value or value.startswith("#"):
            continue
        assert "/api/v1/discovery/machine" not in value


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


def test_discovery_online_runbook_mentions_platform_maintenance() -> None:
    """Discovery online runbook points at the unified platform maintenance workflow."""
    assert DISCOVERY_ONLINE_RUNBOOK.is_file()
    text = DISCOVERY_ONLINE_RUNBOOK.read_text(encoding="utf-8")
    assert "platform-maintenance" in text


def test_discovery_online_runbook_documents_scheduled_first() -> None:
    """Discovery online runbook describes GitHub Actions before laptop debugging."""
    text = DISCOVERY_ONLINE_RUNBOOK.read_text(encoding="utf-8")
    gha_pos = text.lower().find("github actions")
    laptop_pos = text.lower().find("laptop")
    assert gha_pos != -1
    assert laptop_pos != -1
    assert gha_pos < laptop_pos


def test_discovery_online_runbook_documents_idempotency_with_openplz_parity() -> None:
    """Idempotency section cross-links OpenPLZ import runbook."""
    text = DISCOVERY_ONLINE_RUNBOOK.read_text(encoding="utf-8")
    assert "Idempotency" in text or "idempotency" in text
    assert "openplz-import.md" in text
