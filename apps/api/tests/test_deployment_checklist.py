"""Production deployment checklist doc tests (discovery online chapter 9)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKLIST = REPO_ROOT / "docs/operations/deployment-checklist.md"
RENDER_YAML = REPO_ROOT / "render.yaml"


def test_deployment_checklist_mentions_discovery_admin_emails() -> None:
    """Checklist documents DISCOVERY_ADMIN_EMAILS for production Render."""
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "DISCOVERY_ADMIN_EMAILS" in text


def test_render_yaml_does_not_commit_discovery_admin_emails() -> None:
    """Discovery admin allowlist is dashboard-only, not a committed envVar value."""
    text = RENDER_YAML.read_text(encoding="utf-8")
    assert "key: DISCOVERY_ADMIN_EMAILS" not in text
