"""Extraction documentation contracts (chapter E9): what the operations docs must say about the shipped suite."""

from __future__ import annotations

import pytest
from app.config import Settings
from tests.crawlers_docs_support import unqualified_lines
from tests.extraction_docs_support import (
    CHECKLIST,
    DEPLOYMENT_CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    EXTRACTION_DOCS,
    LOOP_DOC,
    REPO_ROOT,
    SCHEDULED_JOBS,
    WORKFLOWS,
    missing,
    read,
    squashed,
)

_NEGATION = ("not ", "no ", "never", "out of scope", "later", "future", "separate", "without", "nothing", "stays")
_OUT_OF_SCOPE_TOPICS = (
    "translate",
    "translation of",
    "per-document tag",
    "edge emit",
    "emit edges",
    "automatic emit",
    "emits automatically",
)


def test_extraction_docs_mention_the_llm_extract_kind_the_neuron_budget_the_ledger_and_release_on_limit() -> None:
    """The drain runbook explains the budgeted kind, both meters, the stop reasons and the release rule."""
    assert not missing(
        DISCOVERY_ONLINE,
        ("`llm_extract`", "--neuron-budget", "neuron", "ledger", "`llm_budget`", "`llm_quota`", "`db_limit`", "4006"),
    )
    assert not missing(DISCOVERY_ONLINE, ("Limits release, pages fail", "release the in-flight", "`no_content`"))
    assert not missing(DISCOVERY_ONLINE, ("`no_documents`", "`login_wall`", "usage.neurons"))
    assert not missing(SCHEDULED_JOBS, ("discovery-llm.yml", "discovery-llm-probe.yml", "DISCOVERY_LLM_SCHEDULE"))


def test_the_drain_runbook_states_that_the_ledger_is_not_the_whole_meter_and_the_dedupe_identity() -> None:
    """Live facts: Cloudflare's own 10,000-neuron allocation counts probes; a re-render queues no second task."""
    assert not missing(DISCOVERY_ONLINE, ("The ledger is not the whole meter", "10,000"))
    assert not missing(DISCOVERY_ONLINE, ("catalogue row, the kind, the target URL", "never queues a second task"))


def test_the_workflow_docs_match_the_llm_workflow_inputs_and_the_render_gap() -> None:
    """The model input is required, the budget default is documented, and the unchanged render workflow is flagged."""
    workflow = read(WORKFLOWS / "discovery-llm.yml")
    assert "required: true" in workflow and "DISCOVERY_LLM_SCHEDULE == 'enabled'" in workflow
    assert "vars.DISCOVERY_LLM_MODEL" in workflow and 'default: "2500"' in workflow
    assert not missing(SCHEDULED_JOBS, ("`llm_model`", "`DISCOVERY_LLM_MODEL`", "`neuron_budget` (2500)"))
    assert "LLM_ENQUEUE" not in read(WORKFLOWS / "discovery-render.yml")
    assert not missing(CHECKLIST, ("LLM_ENQUEUE", "discovery-render.yml", "`env`"))
    assert not missing(SCHEDULED_JOBS, ("`LLM_ENQUEUE:", "discovery-render.yml"))


def test_extraction_docs_state_that_nothing_is_emitted_automatically_and_that_edges_are_staged_not_emitted() -> None:
    """Invariant 4: staging only; edge emit does not exist."""
    assert not missing(DISCOVERY_LAYER, ("Edges are staged, not emitted", "emits nothing"))
    assert not missing(LOOP_DOC, ("Nothing is emitted automatically", "edge emit does not exist"))
    assert "Edge emit" in read(LOOP_DOC).split("## Out of scope", 1)[1]


def test_extraction_docs_state_that_the_workers_ai_token_is_not_a_render_variable_and_the_plan_stays_free() -> None:
    """The token never reaches Render or the API, and the account stays on Workers Free."""
    checklist = squashed(DEPLOYMENT_CHECKLIST)
    assert "CLOUDFLARE_AI_API_TOKEN" in checklist and "**not a Render variable**" in checklist
    assert "Workers **Free**" in checklist and "Workers Paid" in checklist
    assert "BUDGET_NEURONS_DAILY" in checklist and "an API variable" in checklist
    assert "CLOUDFLARE" not in read(REPO_ROOT / "render.yaml")
    assert "cloudflare" not in " ".join(Settings.model_fields)
    assert not missing(CHECKLIST, ("Workers Free", "Do not upgrade to Workers Paid", "OP3"))


def test_extraction_docs_describe_the_grounding_rule_and_the_tag_consensus_threshold_with_the_real_defaults() -> None:
    """The consensus thresholds in the runbook are the Settings defaults; the grounding rule names its drops."""
    assert not missing(DISCOVERY_LAYER, ("Grounding rule", "Tag consensus rule", "tag codes"))
    assert not missing(DISCOVERY_LAYER, ("`DISCOVERY_TAG_MIN_PROCEDURES`", "`DISCOVERY_TAG_MIN_SHARE`"))
    fields = Settings.model_fields
    assert fields["discovery_tag_min_procedures"].default == 2 and fields["discovery_tag_min_share"].default == 0.5
    assert not missing(DISCOVERY_LAYER, ("(default 2)", "(default 0.5)"))
    assert not missing(DEPLOYMENT_CHECKLIST, ("DISCOVERY_TAG_MIN_PROCEDURES", "DISCOVERY_TAG_MIN_SHARE"))


@pytest.mark.parametrize("path", EXTRACTION_DOCS, ids=lambda path: path.name)
def test_docs_do_not_claim_translation_per_document_tags_edge_emit_or_automatic_emit_as_shipped(path) -> None:
    """Negative scope contract: every line about an out-of-scope topic says it is not built."""
    claims = unqualified_lines(path, _OUT_OF_SCOPE_TOPICS, _NEGATION)
    assert not claims, f"{path.name} presents out-of-scope work as shipped: {claims}"


def test_the_scope_check_flags_a_claim_without_a_negation_and_accepts_a_negated_one(tmp_path) -> None:
    """Pair for the scope contract: the detector fires on a positive claim and stays quiet on a denial."""
    page = tmp_path / "page.md"
    page.write_text(
        "The suite ships edge emit.\nEdge emit is out of scope.\nWe translate every name.\n", encoding="utf-8"
    )
    claims = unqualified_lines(page, _OUT_OF_SCOPE_TOPICS, _NEGATION)
    assert claims == ["The suite ships edge emit.", "We translate every name."]
