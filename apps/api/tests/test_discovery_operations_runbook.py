"""Discovery layer operations runbook checks (chapter 22) and the translation runbook checks (azure chapter 16)."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path

from app.config import Settings
from app.features.discovery.budget_resources import BudgetResource

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"
DISCOVERY_ONLINE_RUNBOOK = REPO_ROOT / "docs/operations/discovery-online.md"
SCHEDULED_JOBS = REPO_ROOT / "docs/operations/scheduled-jobs.md"
DEPLOYMENT_CHECKLIST = REPO_ROOT / "docs/operations/deployment-checklist.md"
OPERATOR_CHECKLIST = REPO_ROOT / "docs/operations/crawlers-operator-checklist.md"
POST_DEPLOY_STEPS = REPO_ROOT / "docs/operations/crawlers-post-deploy-human-steps.md"
INGEST_README = REPO_ROOT / "apps/discovery-ingest/README.md"
TRANSLATION_RUNBOOK = REPO_ROOT / "docs/operations/translation-engines.md"
RENDER_YAML = REPO_ROOT / "render.yaml"
API_ENV_EXAMPLE = REPO_ROOT / "apps/api/.env.example"
TRANSLATE_WORKFLOW = REPO_ROOT / ".github/workflows/discovery-translate.yml"
INGEST_PACKAGE = REPO_ROOT / "apps/discovery-ingest/discovery_ingest"
TRANSLATION_NAME = re.compile(r"^(AZURE_|TRANSLATION_|CLAUDE_TRANSLATE_|BUDGET_AZURE_|QUERY_EMBED_RESERVE$)")

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


def _ingest_aliases() -> set[str]:
    """Return the validation alias of every ingest settings field: the names of the variables the worker reads."""
    names: set[str] = set()
    for path in INGEST_PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.keyword)
                and node.arg == "validation_alias"
                and isinstance(node.value, ast.Constant)
            ):
                names.add(str(node.value.value))
    return names


def _api_translation_fields() -> set[str]:
    """Return the API setting names about translation or Azure, spelled as the environment spells them."""
    return {name.upper() for name in Settings.model_fields if "translat" in name or "azure" in name}


def _workflow_names() -> set[str]:
    """Return the GitHub variables and secrets that the translate workflow reads."""
    return set(re.findall(r"\b(?:vars|secrets)\.([A-Z][A-Z0-9_]+)", TRANSLATE_WORKFLOW.read_text(encoding="utf-8")))


def _translation_variables() -> set[str]:
    """Return every translation environment variable that the settings and the translate workflow read."""
    ingest = {name for name in _ingest_aliases() if TRANSLATION_NAME.match(name)}
    return ingest | _api_translation_fields() | _workflow_names()


def _undocumented(names: Iterable[str], text: str) -> list[str]:
    """Return the names that ``text`` does not spell out as whole words, sorted."""
    return sorted(name for name in names if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text))


def test_the_translation_runbook_names_every_translation_variable_that_settings_read() -> None:
    """docs · the translation runbook names every translation variable that the settings and the translate workflow read."""
    text = TRANSLATION_RUNBOOK.read_text(encoding="utf-8")

    assert _undocumented(_translation_variables(), text) == []


def test_a_new_azure_variable_without_documentation_fails_the_docs_check() -> None:
    """docs · a variable added to the settings but not named in the runbook is reported by the same check."""
    text = TRANSLATION_RUNBOOK.read_text(encoding="utf-8")
    added = _translation_variables() | {"AZURE_TRANSLATOR_UNDOCUMENTED"}

    assert _undocumented(added, text) == ["AZURE_TRANSLATOR_UNDOCUMENTED"]


def test_the_cap_defaults_in_the_docs_are_the_config_defaults() -> None:
    """docs · every cap that the docs print is the default of its API setting."""
    for variable, value in _CAP_DEFAULTS.items():
        assert Settings.model_fields[variable.lower()].default == int(value), variable


def test_the_api_env_example_prints_each_cap_at_its_config_default() -> None:
    """docs · the API .env.example shows each cap at its config default."""
    text = API_ENV_EXAMPLE.read_text(encoding="utf-8")

    for variable, value in _CAP_DEFAULTS.items():
        assert re.search(rf"^# {variable}={value}\b", text, re.MULTILINE), variable


def test_the_render_comment_lists_every_cap_variable() -> None:
    """docs · the Render comment names every cap, so the operator sets them from one list."""
    text = RENDER_YAML.read_text(encoding="utf-8")

    assert [variable for variable in _CAP_DEFAULTS if variable not in text] == []


def test_the_deployment_checklist_names_the_six_budget_resources_the_route_returns() -> None:
    """docs · the checklist says the budget route returns six resources, and names each one that BudgetResource defines."""
    text = DEPLOYMENT_CHECKLIST.read_text(encoding="utf-8")
    resources = [resource.value for resource in BudgetResource]

    assert len(resources) == 6 and "returns six resources" in text
    assert [name for name in resources if f"`{name}`" not in text] == []


def test_the_budget_docs_no_longer_say_the_azure_ledger_is_unused() -> None:
    """docs · the scheduled-jobs ledger and the checklist describe the Azure ledger as spent by the translate drain."""
    for doc in (SCHEDULED_JOBS, DEPLOYMENT_CHECKLIST):
        text = doc.read_text(encoding="utf-8")

        assert "No drain reserves it yet" not in text and "Nothing reserves from it until" not in text, doc.name


def test_the_translation_runbook_covers_engines_probe_backfills_rollback_and_the_snapshot_switch() -> None:
    """docs · the runbook covers each chapter 16 topic, and the cost figures that the cost model needs."""
    text = TRANSLATION_RUNBOOK.read_text(encoding="utf-8")
    needles = (
        "TRANSLATION_ENGINE=llm",
        "translate probe --engine azure-translator",
        "TRANSLATION_GLOSSARY_MODE",
        "backfill_translations.py",
        "backfill_snapshot_translations.py",
        "SNAPSHOT_TRANSLATE_SCHEDULE",
        "enable_locale.py",
        "O5",
        "1,900,000",
        "1,140,000",
        "760,000",
    )

    assert [needle for needle in needles if needle not in text] == []


def test_the_translation_runbook_relative_links_resolve() -> None:
    """docs · relative links in the translation runbook resolve to files."""
    text = TRANSLATION_RUNBOOK.read_text(encoding="utf-8")
    missing = [
        rel for rel in _relative_markdown_targets(text) if not (TRANSLATION_RUNBOOK.parent / rel).resolve().is_file()
    ]

    assert missing == []
