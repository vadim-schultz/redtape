"""Production deployment checklist doc tests (discovery online chapter 9)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKLIST = REPO_ROOT / "docs/operations/deployment-checklist.md"
PRODUCTION_SETUP = REPO_ROOT / "docs/operations/discovery-online-production-setup.md"
RENDER_YAML = REPO_ROOT / "render.yaml"


def test_deployment_checklist_mentions_discovery_admin_emails() -> None:
    """Checklist documents DISCOVERY_ADMIN_EMAILS for production Render."""
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "DISCOVERY_ADMIN_EMAILS" in text


def test_render_yaml_does_not_commit_discovery_admin_emails() -> None:
    """Discovery admin allowlist is dashboard-only, not a committed envVar value."""
    text = RENDER_YAML.read_text(encoding="utf-8")
    assert "key: DISCOVERY_ADMIN_EMAILS" not in text


def test_deployment_checklist_documents_worker_discovery_probe_sequence() -> None:
    """Checklist records health, auth, proxy, and JSON discovery checks."""
    text = CHECKLIST.read_text(encoding="utf-8")
    expected = (
        "/health",
        "same-origin",
        "/api/v1/discovery/admin/tasks?limit=1&offset=0",
        "401",
        "403",
        "200",
        "/api/v1/discovery/admin/coverage",
        "/api/v1/discovery/admin/catalogue?limit=50&offset=0",
    )
    positions = [text.index(marker) for marker in expected]
    assert positions == sorted(positions)
    assert "Authorization: Bearer" in text
    assert "valid JSON" in text


def test_production_setup_lists_coverage_route() -> None:
    """Production verification includes the dedicated coverage page."""
    text = PRODUCTION_SETUP.read_text(encoding="utf-8")
    assert "/admin/discovery/coverage" in text
