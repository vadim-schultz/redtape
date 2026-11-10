"""Extraction documentation contracts (chapter E9): what the operations docs must say about the shipped suite."""

from __future__ import annotations

import re

import pytest
from app.config import Settings
from tests.crawlers_docs_support import other_cloudflare_settings, unqualified_lines
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


def test_architecture_section_9_and_the_drain_runbook_state_that_overshoot_is_at_most_one_call() -> None:
    """E19: a call is allowed while the run and the day are below their limits, so the last call may pass them by its own cost."""
    architecture = REPO_ROOT / ".plans/extraction/00-architecture.md"
    sentence = ("may pass the budget by its own cost", "at most one call")
    assert not missing(architecture, sentence)
    assert not missing(DISCOVERY_ONLINE, sentence)


def test_the_workflow_docs_match_the_llm_workflow_inputs_and_the_render_default() -> None:
    """The model input has the code default, the budget default is documented, and the render workflow's default-on LLM_ENQUEUE is documented."""
    workflow = read(WORKFLOWS / "discovery-llm.yml")
    model = re.search(
        r'^DEFAULT_LLM_MODEL = "(@cf/[^"]+)"',
        read(REPO_ROOT / "apps/discovery-ingest/discovery_ingest/llm_settings.py"),
        re.M,
    )
    assert model and f'default: "{model.group(1)}"' in workflow and "required: true" not in workflow
    assert "DISCOVERY_LLM_SCHEDULE == 'enabled'" in workflow
    assert "vars.DISCOVERY_LLM_MODEL" in workflow and 'default: "2500"' in workflow
    assert not missing(
        SCHEDULED_JOBS, ("`llm_model`", "`DISCOVERY_LLM_MODEL`", "`neuron_budget` (2500)", model.group(1))
    )
    assert "LLM_ENQUEUE" in read(WORKFLOWS / "discovery-render.yml")
    assert not missing(CHECKLIST, ("LLM_ENQUEUE", "discovery-render.yml", "`env`"))
    assert not missing(SCHEDULED_JOBS, ("`LLM_ENQUEUE:", "discovery-render.yml"))


def test_extraction_docs_state_that_nothing_is_emitted_automatically_and_that_edges_are_staged_not_emitted() -> None:
    """Invariant 4: staging only; edge emit does not exist."""
    assert not missing(DISCOVERY_LAYER, ("Edges are staged, not emitted", "emits nothing"))
    assert not missing(LOOP_DOC, ("Nothing is emitted automatically", "edge emit does not exist"))
    assert "Edge emit" in read(LOOP_DOC).split("## Out of scope", 1)[1]


def test_extraction_docs_state_that_the_workers_ai_token_is_not_a_render_variable_and_the_plan_stays_free() -> None:
    """The token is not a Render variable yet (search-first D1 lifts that for query embedding) and the plan stays free."""
    checklist = squashed(DEPLOYMENT_CHECKLIST)
    assert "CLOUDFLARE_AI_API_TOKEN" in checklist and "**not a Render variable**" in checklist
    assert "Workers **Free**" in checklist and "Workers Paid" in checklist
    assert "BUDGET_NEURONS_DAILY" in checklist and "an API variable" in checklist
    assert "CLOUDFLARE" not in read(REPO_ROOT / "render.yaml")
    assert not other_cloudflare_settings()
    assert not missing(CHECKLIST, ("Workers Free", "Do not upgrade to Workers Paid", "OP3"))


def test_extraction_docs_describe_the_grounding_rule_and_the_tag_confidence_floor_with_the_real_constant() -> None:
    """The inclusion floor named in the runbook matches tags.py's own constant (situation-tag-hierarchy chapter 1)."""
    from app.features.discovery.tags import MIN_SUGGESTED_SCORE

    assert not missing(DISCOVERY_LAYER, ("Grounding rule", "Tag confidence score", "tag codes"))
    assert not missing(DISCOVERY_LAYER, ("`MIN_SUGGESTED_SCORE`", "noisy-OR"))
    assert MIN_SUGGESTED_SCORE == 0.05
    assert not missing(DISCOVERY_LAYER, ("(0.05)",))
    assert "discovery_tag_min" not in " ".join(Settings.model_fields)


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
