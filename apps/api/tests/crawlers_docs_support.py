"""Shared paths and helpers for the crawlers documentation contract tests (chapter 21)."""

from __future__ import annotations

import re
from pathlib import Path

from app.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]
OPS = REPO_ROOT / "docs/operations"
PLAN = REPO_ROOT / ".plans/crawlers"
WORKFLOWS = REPO_ROOT / ".github/workflows"

DISCOVERY_LAYER = OPS / "discovery-layer.md"
DISCOVERY_ONLINE = OPS / "discovery-online.md"
SCHEDULED_JOBS = OPS / "scheduled-jobs.md"
DEPLOYMENT_CHECKLIST = OPS / "deployment-checklist.md"
GHA_BUDGET = OPS / "gha-budget.md"
SUGGESTION_API = OPS / "suggestion-api.md"
LOOP_DOC = OPS / "loops/crawlers.md"
CHECKLIST = OPS / "crawlers-operator-checklist.md"
INGEST_README = REPO_ROOT / "apps/discovery-ingest/README.md"
PLANS_README = REPO_ROOT / ".plans/README.md"
STATUS = REPO_ROOT / "docs/planning/STATUS.md"
RENDER_YAML = REPO_ROOT / "render.yaml"
GERMAN_SEED = REPO_ROOT / "apps/api/scripts/seed_data/translations/de.json"

QUERY_EMBEDDING_CLOUDFLARE_FIELDS = frozenset({"cloudflare_account_id", "cloudflare_ai_api_token"})
"""The only Cloudflare settings the API holds: the Workers-AI-scoped pair for query embedding (search-first D1)."""


def other_cloudflare_settings() -> frozenset[str]:
    """Return the Cloudflare-named API settings beyond the query-embedding pair; there must be none (no Browser Run or R2 token)."""
    named = frozenset(name for name in Settings.model_fields if "cloudflare" in name)
    return named - QUERY_EMBEDDING_CLOUDFLARE_FIELDS


RUNBOOKS = (
    DISCOVERY_LAYER,
    DISCOVERY_ONLINE,
    SCHEDULED_JOBS,
    DEPLOYMENT_CHECKLIST,
    GHA_BUDGET,
    SUGGESTION_API,
    CHECKLIST,
    INGEST_README,
)

_MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")


def read(path: Path) -> str:
    """Return the UTF-8 text of ``path``."""
    return path.read_text(encoding="utf-8")


def missing_terms(path: Path, terms: tuple[str, ...]) -> list[str]:
    """Return the ``terms`` that ``path`` does not contain."""
    text = read(path)
    return [term for term in terms if term not in text]


def broken_links(path: Path) -> list[str]:
    """Return the relative link targets of ``path`` that name no file or folder."""
    broken: list[str] = []
    for raw in _MARKDOWN_LINK.findall(read(path)):
        target = raw.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (path.parent / target).resolve().exists():
            broken.append(f"{path} -> {raw}")
    return broken


def unqualified_lines(path: Path, topics: tuple[str, ...], negations: tuple[str, ...]) -> list[str]:
    """Return lines naming a ``topic`` with no negation word, outside a section headed "Out of scope"."""
    lines: list[str] = []
    in_scope_section = False
    for line in read(path).splitlines():
        if line.startswith("#"):
            in_scope_section = "out of scope" in line.lower()
        lowered = line.lower()
        if in_scope_section or not any(topic in lowered for topic in topics):
            continue
        if not any(word in lowered for word in negations):
            lines.append(line.strip())
    return lines
