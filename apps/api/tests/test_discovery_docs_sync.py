"""Discovery layer docs sync checks (chapter 23)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS = REPO_ROOT / "docs/planning/STATUS.md"
ROLLOUT = REPO_ROOT / ".plans/discovery-layer/01-rollout.md"
PLANS_README = REPO_ROOT / ".plans/README.md"
GOVERNMENT_DATA_SOURCES = REPO_ROOT / "docs/discovery/government-data-sources.md"
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"
DISCOVERY_ONLINE_RUNBOOK = REPO_ROOT / "docs/operations/discovery-online.md"
SCHEDULED_JOBS = REPO_ROOT / "docs/operations/scheduled-jobs.md"
DISCOVERY_ONLINE_LOOP = REPO_ROOT / "docs/operations/loops/discovery-online.md"

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


def _display_name(markdown_path: Path) -> str:
    """Name a doc relative to the repo root, or by its full path when it lives elsewhere."""
    if markdown_path.is_relative_to(REPO_ROOT):
        return str(markdown_path.relative_to(REPO_ROOT))
    return str(markdown_path)


def _assert_relative_links_resolve(markdown_path: Path) -> None:
    assert markdown_path.is_file(), f"missing doc: {_display_name(markdown_path)}"
    text = markdown_path.read_text(encoding="utf-8")
    base = markdown_path.parent
    missing: list[str] = []
    for rel in _relative_markdown_targets(text):
        resolved = (base / rel).resolve()
        if not (resolved.is_file() or resolved.is_dir()):
            missing.append(rel)
    assert not missing, f"broken relative links in {_display_name(markdown_path)}: {missing}"


def test_status_mentions_discovery_layer_runbook() -> None:
    """STATUS links to the discovery layer operations runbook."""
    text = STATUS.read_text(encoding="utf-8")
    assert "discovery-layer.md" in text
    assert "../operations/discovery-layer.md" in text or "docs/operations/discovery-layer.md" in text


def test_status_records_discovery_layer_shipped() -> None:
    """STATUS records the discovery layer as shipped."""
    text = STATUS.read_text(encoding="utf-8").lower()
    assert "discovery layer" in text
    assert "shipped" in text
    assert "not started" not in text.split("discovery layer", 1)[-1][:400]


def test_plans_readme_marks_discovery_layer_shipped() -> None:
    """Plans index records discovery-layer as shipped."""
    text = PLANS_README.read_text(encoding="utf-8")
    discovery_block = text.split("### [discovery-layer/](discovery-layer/)", 1)[-1]
    assert "Status: shipped" in discovery_block


def test_rollout_in_loop_chapters_marked_shipped() -> None:
    """Rollout table marks in-loop chapters shipped; deferred chapters stay deferred."""
    text = ROLLOUT.read_text(encoding="utf-8")
    chapters_section = text.split("## Chapters", 1)[1]
    for chapter in ("| 1 |", "| 18 |", "| 22 |", "| 23 |"):
        row = next(line for line in chapters_section.splitlines() if line.startswith(chapter))
        assert "| shipped |" in row
    for chapter in ("| 16 |", "| 20 |", "| 21 |"):
        row = next(line for line in chapters_section.splitlines() if line.startswith(chapter))
        assert "| deferred |" in row


def test_edited_planning_docs_relative_links_resolve() -> None:
    """Relative links in chapter-23 edited files resolve."""
    for path in (STATUS, ROLLOUT, PLANS_README):
        _assert_relative_links_resolve(path)


def test_government_data_sources_relative_links_resolve() -> None:
    """Relative links in government data sources canon resolve."""
    _assert_relative_links_resolve(GOVERNMENT_DATA_SOURCES)


def test_runbook_file_exists_for_status_evidence() -> None:
    """Operations runbook referenced from STATUS exists."""
    assert RUNBOOK.is_file()


def test_plans_readme_marks_discovery_online_shipped() -> None:
    """Plans index records discovery-online as shipped."""
    text = PLANS_README.read_text(encoding="utf-8")
    discovery_block = text.split("### [discovery-online/](discovery-online/)", 1)[-1]
    assert "Status: shipped" in discovery_block


def test_discovery_online_docs_relative_links_resolve() -> None:
    """Relative links in discovery-online ops docs resolve."""
    for path in (
        DISCOVERY_ONLINE_RUNBOOK,
        SCHEDULED_JOBS,
        DISCOVERY_ONLINE_LOOP,
        RUNBOOK,
    ):
        _assert_relative_links_resolve(path)


INGEST_README = REPO_ROOT / "apps/discovery-ingest/README.md"
SOURCES_ROUTE = "/machine/candidates/sources"
CAPTURE_REQUEUE = "capture requeue"


def _sources_docs_gaps(runbook: str, ingest_readme: str, online_runbook: str) -> list[str]:
    """Name the docs that miss the sources route or the ``capture requeue`` command."""
    expected = {
        "discovery-layer.md route table": (runbook, SOURCES_ROUTE),
        "discovery-layer.md command": (runbook, CAPTURE_REQUEUE),
        "ingest README": (ingest_readme, CAPTURE_REQUEUE),
        "discovery-online.md": (online_runbook, CAPTURE_REQUEUE),
    }
    return [name for name, (text, needle) in expected.items() if needle not in text]


def test_discovery_docs_list_the_sources_route_and_capture_requeue() -> None:
    """The route table, the ingest README and the laptop drain doc name the sources route and the command."""
    texts = [path.read_text(encoding="utf-8") for path in (RUNBOOK, INGEST_README, DISCOVERY_ONLINE_RUNBOOK)]

    assert _sources_docs_gaps(*texts) == []


def test_sources_docs_check_fails_when_a_doc_drops_the_route_or_the_command() -> None:
    """Negative: text without the route or the command is reported, so removing either from a doc fails the check."""
    runbook = f"| `GET {SOURCES_ROUTE}` | list |\n{CAPTURE_REQUEUE}"

    assert _sources_docs_gaps(runbook, "", "") == ["ingest README", "discovery-online.md"]
    assert _sources_docs_gaps(runbook.replace(SOURCES_ROUTE, ""), CAPTURE_REQUEUE, CAPTURE_REQUEUE) == [
        "discovery-layer.md route table"
    ]
    assert _sources_docs_gaps(runbook.replace(CAPTURE_REQUEUE, ""), CAPTURE_REQUEUE, CAPTURE_REQUEUE) == [
        "discovery-layer.md command"
    ]


CANDIDATE_VIEW_SUITE = REPO_ROOT / ".plans/candidate-view"
CANDIDATE_VIEW_DOC = REPO_ROOT / "docs/operations/candidate-view.md"
CANDIDATE_VIEW_SUITE_FILES = tuple(
    CANDIDATE_VIEW_SUITE / name
    for name in (
        "00-architecture.md",
        "01-rollout.md",
        "02-live-runs.md",
        "gaps-and-decisions.md",
        "run-ledger.md",
    )
)
CANDIDATE_VIEW_HEADINGS = ("## Release smoke checks", "## Deploy order")
# (doc, needle) pairs: each doc must carry the needle once the public candidate view is documented.
CANDIDATE_VIEW_DOC_NEEDLES = {
    "discovery-layer.md links the operator doc": (RUNBOOK, "candidate-view.md"),
    "discovery-layer.md lists the public routes": (RUNBOOK, "/api/v1/candidates"),
    "admin-tables.md notes the header toolbar": (REPO_ROOT / "docs/operations/admin-tables.md", "toolbar"),
    "extraction checklist links the requeue command": (
        REPO_ROOT / "docs/operations/extraction-operator-checklist.md",
        "capture requeue",
    ),
    "STATUS records the candidate view": (STATUS, "candidate view"),
    "loop doc is no longer planned": (REPO_ROOT / "docs/operations/loops/candidate-view.md", "Status\n\nBuilt"),
}


def _candidate_view_doc_gaps() -> list[str]:
    """Name the docs that do not yet mention the public candidate view."""
    return [
        name
        for name, (path, needle) in CANDIDATE_VIEW_DOC_NEEDLES.items()
        if needle not in path.read_text(encoding="utf-8")
    ]


def test_candidate_view_operator_doc_links_resolve() -> None:
    """The operator doc exists and its relative links resolve."""
    _assert_relative_links_resolve(CANDIDATE_VIEW_DOC)


def test_candidate_view_operator_doc_has_the_deploy_order_and_smoke_headings() -> None:
    """The operator doc carries the deploy order and the release smoke checks."""
    lines = CANDIDATE_VIEW_DOC.read_text(encoding="utf-8").splitlines()

    assert [heading for heading in CANDIDATE_VIEW_HEADINGS if heading not in lines] == []


def test_plans_readme_links_the_candidate_view_suite() -> None:
    """The plans index names the suite, its rollout and the operator doc, and marks it built."""
    text = PLANS_README.read_text(encoding="utf-8")
    block = text.split("### [candidate-view/](candidate-view/)", 1)[-1].split("### [", 1)[0]

    assert "candidate-view/01-rollout.md" in block
    assert "operations/candidate-view.md" in block
    assert "Status: built" in block


def test_candidate_view_suite_documents_have_no_broken_relative_links() -> None:
    """The five suite files resolve their relative links."""
    for path in CANDIDATE_VIEW_SUITE_FILES:
        _assert_relative_links_resolve(path)


def test_candidate_view_docs_mention_the_public_view() -> None:
    """The route tables, the admin notes, the indexes and the loop doc describe the public candidate view."""
    assert _candidate_view_doc_gaps() == []


def test_link_checker_reports_the_missing_target(tmp_path: Path) -> None:
    """Negative: a doc with one broken link fails and the failure names that link."""
    (tmp_path / "present.md").write_text("# Present\n", encoding="utf-8")
    doc = tmp_path / "doc.md"
    doc.write_text("[ok](present.md) and [gone](missing/target.md#top)\n", encoding="utf-8")

    with pytest.raises(AssertionError, match=r"missing/target\.md") as failure:
        _assert_relative_links_resolve(doc)

    assert "present.md" not in str(failure.value)


def test_link_checker_names_a_missing_doc(tmp_path: Path) -> None:
    """Negative: a doc that does not exist is reported by its path."""
    with pytest.raises(AssertionError, match="missing doc"):
        _assert_relative_links_resolve(tmp_path / "absent.md")
