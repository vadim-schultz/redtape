"""Crawlers documentation structure contracts (chapter 21): links, indexes, neighbours and the operator checklist."""

from __future__ import annotations

import json
import re

from tests.crawlers_docs_support import (
    CHECKLIST,
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    GERMAN_SEED,
    LOOP_DOC,
    OPS,
    PLAN,
    PLANS_README,
    REPO_ROOT,
    RUNBOOKS,
    STATUS,
    broken_links,
    missing_terms,
    read,
)

_STEPS = [f"S{number}" for number in range(1, 22)] + ["S12b"]
_GERMAN_KEY = re.compile(r"`(discovery_admin\.[a-z0-9_.]+)`")
_APPS_CRAWLER = re.compile(r"apps/crawler\b")
_PLANS = REPO_ROOT / ".plans"


def _german_keys() -> set[str]:
    def flat(node: dict[str, object], prefix: str = "") -> set[str]:
        keys: set[str] = set()
        for name, value in node.items():
            keys |= flat(value, f"{prefix}{name}.") if isinstance(value, dict) else {f"{prefix}{name}"}
        return keys

    return flat(json.loads(read(GERMAN_SEED)))


def test_every_relative_link_in_the_crawlers_plan_folder_the_loop_document_and_the_changed_runbooks_resolves() -> None:
    """No document points at a file that does not exist."""
    documents = [*PLAN.glob("**/*.md"), LOOP_DOC, *RUNBOOKS]
    assert [link for path in documents for link in broken_links(path)] == []


def test_the_link_check_reports_a_missing_target(tmp_path) -> None:
    """Negative pair: a link to a missing file is reported."""
    page = tmp_path / "page.md"
    page.write_text("[gone](missing.md) [here](page.md) [web](https://example.com)", encoding="utf-8")
    assert [link.split(" -> ")[1] for link in broken_links(page)] == ["missing.md"]


def test_the_plans_readme_lists_twenty_three_crawler_chapters_and_no_apps_crawler_package_to_build() -> None:
    """The crawlers entry is current, and `apps/crawler` appears only as the replaced design."""
    block = read(PLANS_README).split("### [crawlers/](crawlers/)", 1)[1].split("### [extraction/]", 1)[0]
    assert "Twenty-three chapters" in block and "queue-based" in block and "feat/crawlers" in block
    assert "Next: [chapters/07" not in block
    assert "### [extraction/](extraction/)" in read(PLANS_README)
    for paragraph in read(PLANS_README).split("\n\n"):
        if _APPS_CRAWLER.search(paragraph):
            assert "replaces" in paragraph.lower() or "earlier" in paragraph.lower(), paragraph


def test_the_operator_checklist_has_every_step_with_an_unticked_box() -> None:
    """S1 to S21 plus S12b each have a row with an open tick box; the operator ticks them."""
    text = read(CHECKLIST)
    rows = {line.split("|")[1].strip(): line for line in text.splitlines() if re.match(r"\| S\d+b? ", line)}
    assert sorted(rows) == sorted(_STEPS)
    assert all("[ ]" in row and "[x]" not in row for row in rows.values())


def test_the_operator_checklist_uses_the_machine_header_and_the_local_probe_routes() -> None:
    """Chapter 22 had the wrong auth header; the checklist and the chapter now show the real one."""
    for text in (read(CHECKLIST), read(PLAN / "chapters/22-operator-manual-steps.md")):
        assert "X-API-Key: $DISCOVERY_API_KEY" in text
        assert "Authorization: Bearer $DISCOVERY_API_KEY" not in text
    assert not missing_terms(
        CHECKLIST,
        (
            "python -m scripts.object_store_probe",
            "discovery_ingest browser probe",
            "artifacts/status",
            "HTTP %{http_code}",
        ),
    )


def test_the_operator_checklist_records_what_is_done_and_what_is_open() -> None:
    """The reported state is written down once, with the steps that still need an action."""
    text = read(CHECKLIST)
    done = text.split("## Reported done", 1)[1].split("## ", 1)[0]
    open_steps = text.split("## Still open", 1)[1].split("## ", 1)[0]
    assert all(step in done for step in ("S1", "S2", "S3", "S4", "S5", "S12b", "S15", "S16", "S19", "S21"))
    assert all(step in open_steps for step in ("S6", "S7", "S10", "S11", "S13", "S14", "S17", "S18", "S20"))
    assert "404" in open_steps and "not yet on `main`" in open_steps


def test_the_german_review_list_names_only_keys_that_exist_and_covers_every_chapter_that_added_some() -> None:
    """Machine-written German needs native review; each key listed exists in the seed, none is missing."""
    listed = set(_GERMAN_KEY.findall(read(CHECKLIST)))
    assert listed and listed <= _german_keys(), sorted(listed - _german_keys())
    prefixes = ("documents.", "artifacts.", "tasks.note_", "document.emit_", "coverage.candidate")
    assert all(any(key.startswith(f"discovery_admin.{prefix}") for key in listed) for prefix in prefixes)
    assert len(listed) >= 88


def test_the_runbooks_link_the_operator_checklist() -> None:
    """The checklist is reachable from the discovery runbooks and the loop document."""
    for path in (DISCOVERY_LAYER, DISCOVERY_ONLINE, LOOP_DOC):
        assert "crawlers-operator-checklist.md" in read(path), path.name
    assert CHECKLIST.is_file()


def test_the_loop_document_records_the_delivered_scope_and_the_known_gaps() -> None:
    """Chapter 21 filled both sections from the ledger."""
    text = read(LOOP_DOC)
    assert "To be filled in by chapter 21" not in text
    assert "Supabase adapter" not in text
    assert not missing_terms(
        LOOP_DOC,
        ("kurztext", "_insert", "discovery_artifact", "Chapter 18", "German", "R2 adapter", "capture_screenshot"),
    )


def test_neighbouring_suites_describe_the_shipped_state() -> None:
    """The planned-amendment notes became statements about what exists."""
    for name in ("00-architecture.md", "01-rollout.md", "gaps-and-decisions.md"):
        text = read(_PLANS / "evidence-storage" / name)
        assert "Planned amendment" not in text and "app/shared/object_store" in text, name
    adapter_plan = read(_PLANS / "discovery-layer/chapters/20-crawler-frontier-adapter.md")
    assert "15 (Cloudflare render" in adapter_plan and "19 (screenshot capture)" in adapter_plan
    assert "Planned amendment" not in read(_PLANS / "suggestion-interface/gaps-and-decisions.md")
    assert "crawlers suite" in read(_PLANS / "discovery-operations/gaps-and-decisions.md")
    assert "deferred" not in _decision(read(_PLANS / "discovery-operations/gaps-and-decisions.md"), "D11").lower()


def _decision(markdown: str, label: str) -> str:
    return next(line for line in markdown.splitlines() if line.startswith(f"| {label} |"))


def test_status_records_the_crawlers_suite_and_points_at_the_operator_checklist() -> None:
    """STATUS says what shipped on the loop branch and what waits for the operator."""
    text = read(STATUS)
    assert "crawlers" in text.lower() and "crawlers-operator-checklist.md" in text
    assert "feat/crawlers" in text


def test_the_stale_throughput_figure_is_gone_from_the_plan_folder() -> None:
    """Chapter 15 measured about 4 pages a minute; the 80-pages-per-run figure only survives in the ledger."""
    offenders = [p.name for p in PLAN.glob("**/*.md") if p.name != "run-ledger.md" and "about 80 pages" in read(p)]
    assert not offenders, offenders
    assert OPS.is_dir()
