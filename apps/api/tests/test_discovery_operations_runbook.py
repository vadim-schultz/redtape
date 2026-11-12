"""Discovery layer operations runbook checks (chapter 22)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"
DISCOVERY_ONLINE_RUNBOOK = REPO_ROOT / "docs/operations/discovery-online.md"
SCHEDULED_JOBS = REPO_ROOT / "docs/operations/scheduled-jobs.md"
DEPLOYMENT_CHECKLIST = REPO_ROOT / "docs/operations/deployment-checklist.md"
OPERATOR_CHECKLIST = REPO_ROOT / "docs/operations/crawlers-operator-checklist.md"
POST_DEPLOY_STEPS = REPO_ROOT / "docs/operations/crawlers-post-deploy-human-steps.md"
INGEST_README = REPO_ROOT / "apps/discovery-ingest/README.md"

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


def test_runbook_documents_complete_admin_route_surface_and_menu_behavior() -> None:
    """Runbook describes every discovery route and its guarded menu links."""
    text = RUNBOOK.read_text(encoding="utf-8")
    for route in (
        "/admin/discovery",
        "/admin/discovery/catalogue",
        "/admin/discovery/coverage",
        "/admin/discovery/tasks",
        "/admin/discovery/pipeline/<catalogue-service-id>",
        "/admin/discovery/unknown",
    ):
        assert route in text
    for menu_label in (
        "Home",
        "Browse Documents",
        "Suggest",
        "Catalogue",
        "Coverage",
        "Tasks",
    ):
        assert menu_label in text
    assert "allowlisted" in text.lower()
    assert "probe" in text.lower()


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


def test_federal_jurisdiction_docs_mention_de_country_query() -> None:
    """Ops canon documents resolving FEDERAL_JURISDICTION_ID from DE country row."""
    de_sql = "kind = 'COUNTRY' AND code = 'DE'"
    online = DISCOVERY_ONLINE_RUNBOOK.read_text(encoding="utf-8")
    scheduled = SCHEDULED_JOBS.read_text(encoding="utf-8")
    checklist = DEPLOYMENT_CHECKLIST.read_text(encoding="utf-8")
    assert de_sql in online
    assert "FEDERAL_JURISDICTION_ID" in online
    assert de_sql in scheduled or "kind=COUNTRY" in scheduled
    assert "FEDERAL_JURISDICTION_ID" in scheduled
    assert "print_federal_jurisdiction_id" in checklist or de_sql in checklist


# Free-tier caps at 95 percent of each allowance (extraction chapter E11): setting -> default as printed in a doc.
_CAP_DEFAULTS = {
    "OBJECT_STORE_MAX_BYTES": "9500000000",
    "BUDGET_R2_CLASS_A_MONTHLY": "950000",
    "BUDGET_R2_CLASS_B_MONTHLY": "9500000",
    "BUDGET_BROWSER_SECONDS_DAILY": "570",
    "BUDGET_NEURONS_DAILY": "9500",
    "BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY": "1900000",
    "DB_SOFT_LIMIT_BYTES": "475000000",
}
_OLD_CAP_DEFAULTS = (
    "8 GiB",
    "8589934592",
    "400 MB",
    "400000000",
    "400,000",
    "4,000,000",
    "400000",
    "4000000",
    "| 480",
    "(480)",
    "default 480",
    "seconds 480",
    "| 8000",
    "| 8,000",
    "(8000)",
)
_CAP_DOCS = (
    RUNBOOK,
    DISCOVERY_ONLINE_RUNBOOK,
    SCHEDULED_JOBS,
    DEPLOYMENT_CHECKLIST,
    OPERATOR_CHECKLIST,
    POST_DEPLOY_STEPS,
    INGEST_README,
)


def _prints_default(text: str, variable: str, value: str) -> bool:
    return re.search(rf"`{variable}`[^\n]*?\b{value}\b", text) is not None


def _standalone(old: str) -> re.Pattern[str]:
    """Match ``old`` only when it is not part of a longer number, such as a URL id."""
    return re.compile(rf"(?<![\w,.]){re.escape(old)}(?![\w,])")


def test_the_operator_checklist_and_the_deployment_checklist_print_the_six_new_caps() -> None:
    """Both documents name every cap variable with its 95 percent default."""
    for doc in (OPERATOR_CHECKLIST, DEPLOYMENT_CHECKLIST):
        text = doc.read_text(encoding="utf-8")
        for variable, value in _CAP_DEFAULTS.items():
            assert _prints_default(text, variable, value), f"{doc.name} must print {variable} = {value}"


def test_the_budget_docs_name_the_azure_character_ledger_and_its_cap() -> None:
    """The deployment checklist lists six budget resources, and the scheduled-jobs ledger has the Azure row."""
    checklist = DEPLOYMENT_CHECKLIST.read_text(encoding="utf-8")
    scheduled = SCHEDULED_JOBS.read_text(encoding="utf-8")

    assert "returns six resources" in checklist
    assert "`azure_translator_chars`" in checklist
    assert "| `azure_translator_chars` | month | 1,900,000 |" in scheduled


def test_the_runbooks_print_the_new_browser_neuron_and_database_numbers() -> None:
    """The scheduled-jobs ledger table, discovery-online, post-deploy steps and ingest README agree."""
    scheduled = SCHEDULED_JOBS.read_text(encoding="utf-8")
    online = DISCOVERY_ONLINE_RUNBOOK.read_text(encoding="utf-8")

    assert "| 570 |" in scheduled and "950,000 and 9,500,000" in scheduled and "| 9,500 |" in scheduled
    assert "`--browser-budget-seconds` | 570 |" in online and "(default 570)" in online
    assert "9.5 GB" in online and "(475 MB)" in online
    assert "soft limit 475 MB" in POST_DEPLOY_STEPS.read_text(encoding="utf-8")
    assert "`--browser-budget-seconds` | 570 |" in INGEST_README.read_text(encoding="utf-8")


def test_no_runbook_still_prints_the_old_caps_as_defaults() -> None:
    """No operations document or README keeps 480 s, 8,000 neurons, 400 MB or 8 GiB as a default."""
    for doc in _CAP_DOCS:
        text = doc.read_text(encoding="utf-8")
        stale = [old for old in _OLD_CAP_DEFAULTS if _standalone(old).search(text)]
        assert not stale, f"{doc.name} still prints the old cap(s) {stale}"
