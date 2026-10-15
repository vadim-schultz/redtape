"""Discovery layer docs sync checks (chapter 23)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS = REPO_ROOT / "docs/planning/STATUS.md"
ROLLOUT = REPO_ROOT / ".plans/discovery-layer/01-rollout.md"
PLANS_README = REPO_ROOT / ".plans/README.md"
GOVERNMENT_DATA_SOURCES = REPO_ROOT / "docs/discovery/government-data-sources.md"
RUNBOOK = REPO_ROOT / "docs/operations/discovery-layer.md"

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


def _assert_relative_links_resolve(markdown_path: Path) -> None:
    assert markdown_path.is_file(), f"missing doc: {markdown_path.relative_to(REPO_ROOT)}"
    text = markdown_path.read_text(encoding="utf-8")
    base = markdown_path.parent
    missing: list[str] = []
    for rel in _relative_markdown_targets(text):
        resolved = (base / rel).resolve()
        if not (resolved.is_file() or resolved.is_dir()):
            missing.append(rel)
    assert not missing, f"broken relative links in {markdown_path.relative_to(REPO_ROOT)}: {missing}"


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
