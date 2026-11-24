"""Real invocations of the ingest CLI from the workflows and the operator docs, as argv lists.

Placeholders are substituted with plausible values (UUIDs, numbers, paths). The source file and line are
in each comment so a reader can find the original. ``test_cli_invocations.py`` parses every entry.
"""

from __future__ import annotations

JURISDICTION = "00000000-0000-0000-0000-000000000001"
SERVICE_ID = "00000000-0000-0000-0000-000000000002"
ARTIFACT_ID = "00000000-0000-0000-0000-000000000003"

INVOCATIONS: tuple[tuple[str, list[str]], ...] = (
    # .github/workflows
    (
        "discovery-llm.yml:99",
        [
            "budget",
            "show",
            "--resource",
            "actions_minutes",
            "--resource",
            "neurons",
            "--require-remaining",
            "actions_minutes=20",
            "--require-remaining",
            "neurons=300",
        ],
    ),
    (
        "discovery-llm.yml:116",
        [
            "worker",
            "drain",
            "--max-tasks",
            "5",
            "--max-batches",
            "4",
            "--time-budget-seconds",
            "600",
            "--neuron-budget",
            "2500",
            "--kinds",
            "llm_extract",
        ],
    ),
    (
        "discovery-llm-probe.yml:62-64",
        [
            "llm",
            "probe",
            "--fixture",
            "tests/fixtures/pages/table_page.html",
            "--max-neurons",
            "900",
            "--model",
            "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        ],
    ),
    ("discovery-fixture-capture.yml:63", ["artifacts", "list", "--host", "verwaltung.bund.de", "--limit", "20"]),
    ("discovery-fixture-capture.yml:66", ["artifacts", "download", "--id", ARTIFACT_ID, "--out", "fixtures/page.html"]),
    (
        "discovery-screenshot.yml:87",
        [
            "budget",
            "show",
            "--resource",
            "actions_minutes",
            "--resource",
            "browser_seconds",
            "--require-remaining",
            "actions_minutes=20",
            "--require-remaining",
            "browser_seconds=30",
        ],
    ),
    (
        "discovery-screenshot.yml:109-111",
        [
            "worker",
            "drain",
            "--max-tasks",
            "5",
            "--max-batches",
            "40",
            "--time-budget-seconds",
            "900",
            "--browser-budget-seconds",
            "570.0",
            "--kinds",
            "capture_screenshot",
        ],
    ),
    ("discovery-screenshot.yml:144", ["budget", "report-minutes", "--minutes", "4"]),
    (
        "discovery-render.yml:108-115",
        [
            "worker",
            "drain",
            "--max-tasks",
            "5",
            "--max-batches",
            "40",
            "--time-budget-seconds",
            "900",
            "--browser-budget-seconds",
            "570.0",
            "--kinds",
            "render_page",
        ],
    ),
    (
        "discovery-browser-probe.yml:68-75",
        [
            "browser",
            "probe",
            "--max-browser-seconds",
            "240",
            "--url",
            "https://example.com",
            "--error-url",
            "https://example.invalid",
            "--variant",
            "content",
        ],
    ),
    ("discovery-fim-probe.yml:47", ["fim", "probe", "--keys", "99154021000000,99070016261000"]),
    (
        "platform-maintenance.yml:98-101",
        ["govdata", "fetch", "--jurisdiction-id", JURISDICTION, "--max-pages", "15", "--page-size", "100"],
    ),
    ("platform-maintenance.yml:106-108", ["pvog", "run", "--jurisdiction-id", JURISDICTION, "--max-pages", "50"]),
    # docs (operator guides, apps/discovery-ingest/README.md)
    (
        "docs/operations/discovery-online.md (govdata run)",
        ["govdata", "run", "--input", "leistungen.json", "--jurisdiction-id", JURISDICTION],
    ),
    ("docs/operations/discovery-online.md (pvog run)", ["pvog", "run", "--jurisdiction-id", JURISDICTION]),
    (
        "docs/operations/discovery-online.md (fim enrich)",
        [
            "fim",
            "enrich",
            "--catalogue-service-id",
            SERVICE_ID,
            "--catalogue-export",
            "export.json",
            "--input",
            "steckbrief.json",
        ],
    ),
    (
        "docs/operations/discovery-online.md (leika enrich)",
        [
            "leika",
            "enrich",
            "--catalogue-service-id",
            SERVICE_ID,
            "--catalogue-export",
            "export.json",
            "--input",
            "stammtext.json",
        ],
    ),
    (
        "docs/operations/candidate-curation (emit dry run)",
        ["candidates", "emit", "--all-staged", "--min-mentions", "3", "--limit", "5", "--dry-run"],
    ),
    (
        "docs/operations/candidate-curation (emit by id)",
        ["candidates", "emit", "--id", SERVICE_ID, "--id", ARTIFACT_ID],
    ),
    (
        "docs/operations/candidate-curation (page)",
        ["candidates", "page", "--candidate-id", SERVICE_ID, "--out", "pages/"],
    ),
    (
        "docs/operations/candidate-curation/showcase.json (curate dry run)",
        ["candidates", "curate", "--file", "docs/operations/candidate-curation/showcase.json", "--dry-run"],
    ),
    (
        "docs/operations/candidate-curation/showcase.json (curate)",
        ["candidates", "curate", "--file", "docs/operations/candidate-curation/showcase.json"],
    ),
    ("docs/operations (budget show)", ["budget", "show", "--resource", "neurons"]),
    ("docs/operations (llm requeue dry run)", ["llm", "requeue", "--limit", "20", "--dry-run"]),
    ("docs/operations (llm requeue host)", ["llm", "requeue", "--host", "verwaltung.bund.de", "--limit", "50"]),
    (
        "docs/operations (llm eval)",
        ["llm", "eval", "--model", "@cf/meta/llama-3.1-8b-instruct", "--neuron-budget", "4000", "--out", "eval-1.json"],
    ),
    (
        "docs/operations (capture requeue)",
        [
            "capture",
            "requeue",
            "--host",
            "verwaltung.bund.de",
            "--limit",
            "50",
            "--service-id",
            SERVICE_ID,
            "--dry-run",
        ],
    ),
    (
        "docs/operations (drain llm_extract)",
        [
            "worker",
            "drain",
            "--kinds",
            "llm_extract",
            "--max-tasks",
            "1",
            "--max-batches",
            "1",
            "--neuron-budget",
            "1000",
        ],
    ),
    ("docs/operations (browser probe)", ["browser", "probe", "--url", "https://example.com", "--variant", "content"]),
    (
        "docs/operations (artifacts download)",
        ["artifacts", "download", "--id", ARTIFACT_ID, "--out", "tests/fixtures/verwaltung/page.html"],
    ),
)
"""Every argv the operator and the workflows run; ``test_cli_invocations`` parses each one."""
