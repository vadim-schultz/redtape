"""Docs sync checks of the document-browse-confidence suite (chapter 10)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_discovery_docs_sync import _assert_relative_links_resolve

REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = REPO_ROOT / "docs/operations"
CANDIDATE_VIEW = OPERATIONS / "candidate-view.md"
ADMIN_TABLES = OPERATIONS / "admin-tables.md"
DEPLOYMENT_CHECKLIST = OPERATIONS / "deployment-checklist.md"
DISCOVERY_LAYER = OPERATIONS / "discovery-layer.md"
SUGGESTION_API = OPERATIONS / "suggestion-api.md"
STATUS = REPO_ROOT / "docs/planning/STATUS.md"
ROADMAP = REPO_ROOT / "docs/planning/02-incremental-mvp-roadmap.md"
PLANS_README = REPO_ROOT / ".plans/README.md"
MENU_ARCHITECTURE = REPO_ROOT / ".plans/frontend-ui-menu/00-architecture.md"
SUITE = "document-browse-confidence"

# (doc, needle): each doc must carry the needle once the candidate-backed document list is documented.
PRESENT = {
    "candidate-view: the candidate API backs /documents": (CANDIDATE_VIEW, "`/documents`"),
    "candidate-view: sort by confidence": (CANDIDATE_VIEW, "`confidence`"),
    "candidate-view: the code cap": (CANDIDATE_VIEW, "at most 20 codes"),
    "candidate-view: no floor": (CANDIDATE_VIEW, "no 0.05 floor"),
    "candidate-view: redirect": (CANDIDATE_VIEW, "`/candidates` redirects to `/documents`"),
    "candidate-view: smoke check names the confidence circle": (CANDIDATE_VIEW, "confidence circle"),
    "admin-tables: /suggestions keeps its 20-row limit": (ADMIN_TABLES, "`/suggestions` shows at most 20 rows"),
    "deployment-checklist: candidate-backed documents smoke": (DEPLOYMENT_CHECKLIST, "confidence circle"),
    "discovery-layer: dormant emit, vote, promote": (DISCOVERY_LAYER, "**dormant**"),
    "discovery-layer: floor only on the emit payload": (DISCOVERY_LAYER, "only to the emit payload"),
    "suggestion-api: dormant": (SUGGESTION_API, "dormant"),
    "suggestion-api: no web link to the submit form": (SUGGESTION_API, "`/suggest`"),
    "STATUS: candidate-backed list": (STATUS, SUITE),
    "roadmap: candidate-backed list": (ROADMAP, SUITE),
    "plans README: suite shipped": (PLANS_README, "Status: shipped"),
    "menu architecture: closes on select": (MENU_ARCHITECTURE, "closes on select"),
}
# (doc, needle): stale statements that must be gone.
ABSENT = {
    "candidate-view: the old candidates list route": (CANDIDATE_VIEW, "| Web | `/candidates` | The ranked list"),
    "candidate-view: the old menu check": (CANDIDATE_VIEW, "The menu has a Candidates icon link"),
    "admin-tables: first 20 for /documents": (ADMIN_TABLES, "Public `/documents` and `/suggestions` are not part"),
    "deployment-checklist: empty documents list": (DEPLOYMENT_CHECKLIST, "`total` is `0` until a candidate"),
    "discovery-layer: removed Suggest menu link": (DISCOVERY_LAYER, "| **Suggest** |"),
    "discovery-layer: public candidates list": (DISCOVERY_LAYER, "| `/candidates` | Lists every staged"),
    "suggestion-api: not yet built voting suite": (SUGGESTION_API, "not yet built"),
    "menu architecture: Suggest link in the diagram": (MENU_ARCHITECTURE, "Documents link · Suggest link"),
}


def _present(pairs: dict[str, tuple[Path, str]]) -> list[str]:
    """Name the entries whose doc carries the needle."""
    return [name for name, (path, needle) in pairs.items() if needle in path.read_text(encoding="utf-8")]


def _missing(pairs: dict[str, tuple[Path, str]]) -> list[str]:
    """Name the entries whose doc lacks the needle."""
    present = set(_present(pairs))
    return [name for name in pairs if name not in present]


def test_docs_describe_the_candidate_backed_document_list() -> None:
    """Happy path: each doc carries its statement about the candidate-backed list and the dormant stack."""
    assert _missing(PRESENT) == []


def test_docs_drop_the_stale_statements() -> None:
    """Negative path: the retired list, menu link, seeded-document and voting statements are gone."""
    assert _present(ABSENT) == []


def test_plans_readme_marks_the_suite_shipped_in_its_own_block() -> None:
    """The index entry of this suite, not another one, carries the shipped status."""
    text = PLANS_README.read_text(encoding="utf-8")
    block = text.split(f"### [{SUITE}/]({SUITE}/)", 1)[-1].split("### [", 1)[0]

    assert "Status: shipped" in block
    assert "Status: planned" not in block


@pytest.mark.parametrize("doc", [CANDIDATE_VIEW, ADMIN_TABLES, DEPLOYMENT_CHECKLIST, DISCOVERY_LAYER, SUGGESTION_API])
def test_edited_operator_docs_keep_their_relative_links(doc: Path) -> None:
    """Every relative link of an edited operator doc resolves."""
    _assert_relative_links_resolve(doc)


def test_the_stale_statement_check_reports_a_present_needle(tmp_path: Path) -> None:
    """Negative: the checker names a doc that still carries a stale statement."""
    doc = tmp_path / "doc.md"
    doc.write_text("still says first 20 rows\n", encoding="utf-8")

    assert _present({"stale": (doc, "first 20 rows")}) == ["stale"]
    assert _missing({"gone": (doc, "not there")}) == ["gone"]
