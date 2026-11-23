"""Crawlers documentation contracts (chapter 21): what the operations docs must say about the shipped suite."""

from __future__ import annotations

import re
from typing import get_args

import pytest
from app.config import Settings
from app.models.discovery.enums import DiscoveryTaskKind
from app.schema.discovery.machine import StopReason
from tests.crawlers_docs_support import (
    DEPLOYMENT_CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    GHA_BUDGET,
    INGEST_README,
    LOOP_DOC,
    OPS,
    RENDER_YAML,
    SCHEDULED_JOBS,
    WORKFLOWS,
    missing_terms,
    other_cloudflare_settings,
    read,
    unqualified_lines,
)

_PLAYWRIGHT_INSTRUCTION = re.compile(
    r"playwright install|pip install[^\n]*playwright|\[capture\]|install chromium", re.I
)
_OUT_OF_SCOPE_TOPICS = ("link-following", "freshness crawling", "llm extraction", "requirement emit")
_NEGATION = ("not ", "no ", "never", "out of scope", "later", "future", "separate", "without", "planned")


def test_crawl_docs_mention_the_kind_filter_bounded_drain_retry_and_manual_candidate_emit() -> None:
    """The runbooks describe the claim filter, the bounded drain, backoff, `remaining` and the emit CLI."""
    assert not missing_terms(
        DISCOVERY_ONLINE,
        (
            "--kinds",
            "--max-batches",
            "--time-budget-seconds",
            "backoff",
            "tasks/summary",
            "pending_ready",
            "`remaining`",
        ),
    )
    assert not missing_terms(
        DISCOVERY_LAYER,
        ("candidates emit", "--dry-run", "--all-staged", "emit-preview", "harvest_payload", "extract_page"),
    )


def test_crawl_docs_no_longer_say_that_remaining_is_unknown() -> None:
    """The pre-chapter-5 claim that no queue summary exists is gone from the drain runbook."""
    assert "No queue-summary route" not in read(DISCOVERY_ONLINE)
    assert "so each scheduled run is one batch" not in read(DISCOVERY_ONLINE)


def test_crawl_docs_state_that_procedures_are_not_documents() -> None:
    """A catalogue service is a procedure; only what it requires or provides is a document candidate."""
    text = read(DISCOVERY_LAYER).lower()
    assert "a procedure is not a document" in text
    assert "mention" in text and "candidate" in text
    assert "service-level" in text
    assert "a procedure is not a document" in read(LOOP_DOC).lower() or "procedure, not a document" in read(LOOP_DOC)


def test_crawl_docs_document_the_object_store_settings_the_503_behaviour_and_the_507_byte_cap() -> None:
    """The deployment checklist names every storage variable, the optional boot and both status codes."""
    names = sorted(name.upper() for name in Settings.model_fields if name.startswith("object_store_"))
    assert not missing_terms(DEPLOYMENT_CHECKLIST, (*names, "r2.cloudflarestorage.com", "`auto`", "503", "507"))
    assert not missing_terms(DEPLOYMENT_CHECKLIST, ("never in `render.yaml`", "still boots"))


def test_storage_credentials_stay_out_of_render_yaml_and_the_drain_workflows() -> None:
    """Invariant 5: only the probe workflow receives object-store credentials, and none is committed."""
    assert "key: OBJECT_STORE" not in read(RENDER_YAML)
    for workflow in ("discovery-drain.yml", "discovery-render.yml", "discovery-fixture-capture.yml"):
        assert "OBJECT_STORE" not in read(WORKFLOWS / workflow)
    assert "discovery-storage-probe.yml" in read(SCHEDULED_JOBS)


def test_crawl_docs_document_the_cloudflare_browser_budget_the_release_on_limit_rule_and_the_token_scope() -> None:
    """Browser limits release tasks, and the Browser Run token is deliberately not a Render variable or an API setting."""
    assert not missing_terms(
        DISCOVERY_ONLINE,
        (
            "browser_budget",
            "browser_quota",
            "429",
            "released",
            "10 browser minutes",
            "11 seconds",
            "Browser Run - Edit",
        ),
    )
    checklist = read(DEPLOYMENT_CHECKLIST)
    assert "CLOUDFLARE_BROWSER_API_TOKEN" in checklist
    assert "not a Render variable" in checklist
    assert not other_cloudflare_settings()
    assert "CLOUDFLARE" not in read(RENDER_YAML)


def test_the_operations_docs_and_the_ingest_readme_do_not_tell_anyone_to_install_playwright_or_a_capture_extra() -> (
    None
):
    """Negative contract for the removed design; the pattern is proven to match an install instruction."""
    assert _PLAYWRIGHT_INSTRUCTION.search("run: playwright install chromium")
    offenders = [p.name for p in (*OPS.glob("**/*.md"), INGEST_README) if _PLAYWRIGHT_INSTRUCTION.search(read(p))]
    assert not offenders, f"install instructions for a browser in: {offenders}"


@pytest.mark.parametrize("path", [DISCOVERY_LAYER, DISCOVERY_ONLINE, LOOP_DOC, INGEST_README])
def test_crawl_docs_do_not_claim_link_following_freshness_llm_extraction_or_requirement_emit_as_shipped(path) -> None:
    """Every line about an out-of-scope topic says it is not built."""
    claims = unqualified_lines(path, _OUT_OF_SCOPE_TOPICS, _NEGATION)
    assert not claims, f"{path.name} presents out-of-scope work as shipped: {claims}"


def test_the_loop_doc_lists_the_out_of_scope_topics() -> None:
    """The positive side of the scope contract: the loop document names them as future work."""
    text = read(LOOP_DOC).lower()
    assert all(topic in text for topic in ("link-following", "freshness crawling", "llm extraction", "new_requirement"))


def test_crawl_docs_state_the_free_allocation_caps_and_that_actions_minutes_are_not_metered() -> None:
    """Each cap the ledger enforces is written down, and this repository's Actions minutes are not metered (D17)."""
    assert not missing_terms(DEPLOYMENT_CHECKLIST, ("BUDGET_R2_CLASS_A_MONTHLY", "BUDGET_R2_CLASS_B_MONTHLY"))
    assert not missing_terms(
        DEPLOYMENT_CHECKLIST, ("BUDGET_BROWSER_SECONDS_DAILY", "DB_SOFT_LIMIT_BYTES", "9500000000")
    )
    assert not missing_terms(GHA_BUDGET, ("not metered", "D17", "budget show"))
    assert not missing_terms(SCHEDULED_JOBS, ("actions_minutes", "browser_seconds", "report-minutes"))


def test_no_document_assumes_about_960_minutes_as_a_forward_looking_share() -> None:
    """October's 960 minutes stay as history; no document budgets with them."""
    for path in OPS.glob("**/*.md"):
        for line in read(path).splitlines():
            if "960" in line:
                assert "October" in line or "used" in line, f"{path.name}: {line.strip()}"
    assert "Assume about 960" not in read(GHA_BUDGET)


def test_the_drain_runbook_names_every_stop_reason_and_the_render_throughput() -> None:
    """The stop reasons the API accepts are documented, with the measured render rate."""
    assert not missing_terms(DISCOVERY_ONLINE, get_args(StopReason))
    assert not missing_terms(DISCOVERY_ONLINE, ("about 4 pages a minute", "55", "22 runs"))
    assert "80 pages" not in read(DISCOVERY_ONLINE)


def test_the_runbook_names_every_task_kind_the_api_knows() -> None:
    """The discovery-layer runbook has a row for each `discovery_task_kind` value."""
    assert not missing_terms(DISCOVERY_LAYER, tuple(kind.value for kind in DiscoveryTaskKind))
