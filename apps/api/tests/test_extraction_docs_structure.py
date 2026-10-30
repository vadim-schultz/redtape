"""Extraction documentation structure contracts (chapter E9): links, indexes, neighbours, checklist and the code."""

from __future__ import annotations

import re

from tests.crawlers_docs_support import broken_links
from tests.extraction_docs_support import (
    CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    GOLD_README,
    INGEST_README,
    LOOP_DOC,
    PLAN,
    PLANS_README,
    REPO_ROOT,
    SCHEDULED_JOBS,
    constant,
    missing,
    read,
)

_PLANS = REPO_ROOT / ".plans"
_STEPS = [f"OP{number}" for number in range(1, 17)]
_STALE_VERSION = re.compile(r"\bext-[1-4]\b")


def _extraction_block() -> str:
    return read(PLANS_README).split("### [extraction/](extraction/)", 1)[1].split("### [discovery-layer/]", 1)[0]


def test_every_relative_link_in_the_extraction_plan_folder_the_loop_document_and_the_changed_runbooks_resolves() -> (
    None
):
    """No document points at a file that does not exist."""
    documents = [*PLAN.glob("**/*.md"), LOOP_DOC, CHECKLIST, DISCOVERY_LAYER, DISCOVERY_ONLINE, SCHEDULED_JOBS]
    documents += [INGEST_README, PLANS_README, GOLD_README]
    assert [link for path in documents for link in broken_links(path)] == []


def test_the_plans_readme_lists_twenty_extraction_chapters_and_their_state() -> None:
    """The entry counts E1 to E20, is current, and names the release state and the pending decision."""
    block = _extraction_block()
    assert (
        "Twenty chapters" in block
        and "Eighteen chapters" not in block
        and "Nine chapters" not in block
        and "no chapter started" not in block
    )
    assert not missing_in(block, ("feat/extraction", "PR #229", "X16", "extraction-operator-checklist.md"))
    chapter_files = sorted(path.name for path in (PLAN / "chapters").glob("[0-9][0-9]-*.md"))
    assert len(chapter_files) == 20
    index = read(PLAN / "chapters/README.md")
    assert all(f"({name})" in index for name in chapter_files)


def test_the_rollout_table_has_twenty_rows_whose_status_matches_the_ledger() -> None:
    """The rollout agrees with the ledger: a chapter is `merged` in both or `planned` in both."""
    rollout = read(PLAN / "01-rollout.md")
    rows = [line for line in rollout.splitlines() if re.match(r"\| E\d+ \|", line)]
    assert len(rows) == 20 and "Twenty independently shippable chapters" in rollout
    ledger = {
        line.split("|")[1].strip(): line.split("|")[3].strip()
        for line in read(PLAN / "run-ledger.md").splitlines()
        if re.match(r"\| E\d+ \|", line)
    }
    for row in rows:
        cells = [cell.strip() for cell in row.split("|")]
        chapter, status = cells[1], cells[-2]
        assert status in {"merged", "planned"} or status.startswith("merged"), row
        assert ledger[chapter].startswith(status.split(" ")[0]), (chapter, status, ledger[chapter])


def test_the_stale_version_pattern_matches_an_old_prompt_version_and_the_link_check_reports_a_missing_file(
    tmp_path,
) -> None:
    """Negative pair: the checks above would fire on the old text and on a dead link."""
    assert _STALE_VERSION.findall("must match the checkout (`ext-2`)") == ["ext-2"]
    assert _STALE_VERSION.findall("currently `ext-5`") == []
    page = tmp_path / "page.md"
    page.write_text("[gone](missing.md)", encoding="utf-8")
    assert len(broken_links(page)) == 1


def test_the_operator_checklist_has_every_step_with_an_open_box_and_the_live_gate_commands() -> None:
    """OP1 to OP16 each have a row with an open tick box, and the deferred live gates carry exact commands."""
    text = read(CHECKLIST)
    rows = {line.split("|")[1].strip(): line for line in text.splitlines() if re.match(r"\| OP\d+ ", line)}
    assert sorted(rows, key=lambda step: int(step[2:])) == _STEPS
    assert all("[ ]" in row and "[x]" not in row for row in rows.values())
    assert not missing(
        CHECKLIST,
        (
            "llm probe",
            "llm eval",
            "llm requeue",
            "budget show",
            "worker drain --kinds llm_extract",
            "gh workflow run discovery-llm.yml",
            "pg_database_size",
            "robots.txt disallows",
            "discovery-fixture-capture.yml",
            "final release PR",
            "PR #229",
            "Actions minutes are exhausted until the end of October",
        ),
    )


def test_the_operator_checklist_names_the_deploy_note_and_the_pending_decisions() -> None:
    """The E8 deploy note, the gold review and the model decision are written down once."""
    assert not missing(CHECKLIST, ("`llm_outcomes`", "deploy API and web in the same window", "seeds translations"))
    assert not missing(CHECKLIST, ("gold labels", "X16", "@cf/qwen/qwen3-30b-a3b-fp8", "E6 dry smoke", "E10 re-pend"))


def test_the_docs_name_the_current_prompt_and_cleaner_versions_and_no_older_prompt_version() -> None:
    """The versions in the code are the versions in the docs; `ext-2` no longer appears as the current one."""
    prompt = constant("discovery_ingest/extract/llm/prompt.py", "PROMPT_VERSION")
    clean = constant("discovery_ingest/extract/clean.py", "CLEAN_VERSION")
    assert not missing(LOOP_DOC, (f"`{prompt}`", f"`{clean}`"))
    assert not missing(INGEST_README, (f"`{prompt}`", f"`{clean}`"))
    assert not missing(DISCOVERY_LAYER, (f"`{prompt}`", f"`{clean}`"))
    assert "must match the checkout (`ext-2`)" not in read(INGEST_README)
    assert [m for m in _STALE_VERSION.findall(read(INGEST_README)) if m != prompt] == []
    assert "(`ext-1`)" not in read(GOLD_README)


def test_the_docs_name_the_real_settings_and_commands_of_the_ingest_package() -> None:
    """Values come from the code: output limit, character cap, model default, neuron flag and the CLI surface."""
    tokens = constant("discovery_ingest/llm_settings.py", "DEFAULT_MAX_TOKENS")
    chars = constant("discovery_ingest/extract/clean.py", "DEFAULT_MAX_CHARS")
    settings = read(REPO_ROOT / "apps/discovery-ingest/discovery_ingest/llm_settings.py")
    default_model = re.search(r'^DEFAULT_LLM_MODEL = "(@cf/[^"]+)"', settings, re.M)
    assert default_model and "llm_model: str = Field(default=DEFAULT_LLM_MODEL" in settings
    assert not missing(INGEST_README, (f"output limit ({tokens} tokens)", f"({chars}, the cleaner's cap)"))
    assert not missing(INGEST_README, ("Defaults to", default_model.group(1), "X16", "--neuron-budget"))
    for doc in (SCHEDULED_JOBS, CHECKLIST, LOOP_DOC, DISCOVERY_ONLINE):
        assert default_model.group(1) in read(doc) and "provisional" in read(doc), doc
    assert not missing(INGEST_README, ("`llm probe", "`llm eval", "`llm requeue", "`budget show`"))
    cli = read(REPO_ROOT / "apps/discovery-ingest/discovery_ingest/cli.py")
    assert all(f'"{command}"' in cli for command in ("requeue", "probe", "eval", "budget"))


def test_neighbouring_suites_point_at_the_extraction_suite() -> None:
    """Discovery-layer chapter 21 is superseded, and the crawlers seam row and loop document point at the shipped suite."""
    chapter = read(_PLANS / "discovery-layer/chapters/21-llm-extract-flag.md")
    assert "**Status:** superseded" in chapter and "Status:** deferred" not in chapter
    assert "superseded" in read(_PLANS / "discovery-layer/chapters/README.md")
    row = next(
        line for line in read(_PLANS / "crawlers/gaps-and-decisions.md").splitlines() if "| LLM extraction |" in line
    )
    assert "Built as its own suite" in row and "Planned as its own suite" not in row
    assert "extraction.md" in read(REPO_ROOT / "docs/operations/loops/crawlers.md")


def test_the_architecture_and_the_e3_chapter_describe_the_normalisation_that_was_built() -> None:
    """E13 made the quote check symmetric; the stale 'whitespace only' description is gone."""
    architecture = read(PLAN / "00-architecture.md")
    assert "after whitespace normalisation, a substring" not in architecture
    assert not missing(
        PLAN / "00-architecture.md", ("**both** sides", "list bullets removed anywhere after whitespace")
    )
    assert not missing(PLAN / "chapters/03-extraction-schema-and-grounding.md", ("E13", "made it symmetric", "E12"))
    assert "llm:<schema_version>:<model>" not in architecture


def test_the_loop_document_has_the_chief_of_staff_sections_and_the_known_gaps() -> None:
    """Same sections as `loops/crawlers.md`, filled from the ledger."""
    text = read(LOOP_DOC)
    for heading in (
        "## How to run",
        "## Operator dependencies",
        "## Rules for implementers",
        "## What the suite delivers",
        "## Known gaps",
        "## Out of scope",
    ):
        assert heading in text, heading
    assert not missing(LOOP_DOC, ("feat/extraction", ".plans/extraction/", "E7, E8, E9 and E12 to E18", "PR #229"))
    assert not missing(LOOP_DOC, ("X16", "gold labels", "discovery-render.yml", "Actions minutes are exhausted"))


def missing_in(text: str, terms: tuple[str, ...]) -> list[str]:
    """Return the ``terms`` that ``text`` does not contain, ignoring line wraps."""
    squashed = " ".join(text.split())
    return [term for term in terms if term not in squashed]
