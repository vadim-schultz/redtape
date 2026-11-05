"""Chapter 9 reference scan: retired taxonomy identifiers stay out of runtime code, contracts, fixtures and active docs.

The allowlist names only the frozen artifacts that must keep legacy vocabulary: the crosswalk contract, the
archive definitions the historical migrations replay, and the retirement tests that assert the absence itself.
Historical Alembic revisions and ``.plans/`` artifacts are never scanned.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CODE_GLOBS = (
    "apps/api/app/**/*.py",
    "apps/api/scripts/**/*.py",
    "apps/api/tests/**/*.py",
    "apps/api/tests/fixtures/*.json",
    "apps/web/src/**/*.ts",
    "apps/web/src/**/*.tsx",
    "apps/web/src/**/*.json",
)
DOC_GLOBS = (
    "docs/operations/*.md",
    "docs/planning/directions/**/*.md",
)

ALLOWED_FILES = frozenset(
    {
        "apps/api/app/shared/retired_taxonomy.py",
        "apps/api/scripts/category_backfill.py",
        "apps/api/scripts/category_mention_projection.py",
        "apps/api/scripts/seed_data/category_contract.py",
        "apps/api/scripts/seed_data/legacy_tables.py",
        "apps/api/scripts/legacy_taxonomy_archive.py",
        "apps/api/tests/test_c4_category_contract.py",
        "apps/api/tests/test_category_backfill.py",
        "apps/api/tests/test_discovery_staging_migration_retry.py",
        "apps/api/tests/test_document_repository.py",
        "apps/api/tests/test_document_service.py",
        "apps/api/tests/test_documents_filter.py",
        "apps/api/tests/test_remove_seeded_documents_migration.py",
        "apps/api/tests/test_suggestion_payload.py",
        "apps/api/tests/test_taxonomy_api.py",
        "apps/api/tests/test_legacy_taxonomy_retirement.py",
        "apps/api/tests/test_legacy_reference_scan.py",
        "apps/api/tests/test_legacy_taxonomy_migration.py",
        "apps/web/src/test/contract/contract.test.ts",
        "apps/web/src/test/contract/openapi.schemas.json",
    }
)

CODE_PATTERNS = (
    r"api/v1/(matrix|domains|life-situations|life-situation-groups)\b",
    r"\bfetch(Domains|LifeSituations|LifeSituationGroups|Matrix)\b",
    r"\buse(Domains|LifeSituations|LifeSituationGroups)Query\b",
    r"\bdocument_domain\b|\bdocument_life_situation\b",
    r"\blife_situation_group\b|\bLifeSituationGroup\b|\bLifeSituation\b",
    r"\bdomain_codes\b|\bsituation_codes\b",
    r"\bdirect_(domain|situation)_confidence\b",
    r"\bMatrix(Response|Cell)\b|\bget_matrix\b|\bmatrix_counts\b",
    r"\bfilter\[(domain|situation|group)\]",
    r"\bfilter_(domain|situation|group)\b",
)
DOC_PATTERNS = (
    r"api/v1/(matrix|domains|life-situations|life-situation-groups)\b",
    r"filter\[(domain|situation|group)\]",
    r"[?&](domain|situation|group)=",
)


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _files(globs: Iterable[str]) -> list[Path]:
    return sorted({path for pattern in globs for path in REPO_ROOT.glob(pattern) if path.is_file()})


def _offenders(paths: Iterable[Path], patterns: tuple[str, ...]) -> list[str]:
    compiled = [re.compile(pattern) for pattern in patterns]
    hits: list[str] = []
    for path in paths:
        relative = _relative(path)
        if relative in ALLOWED_FILES:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if any(pattern.search(line) for pattern in compiled):
                hits.append(f"{relative}:{number}: {line.strip()[:120]}")
    return hits


def test_runtime_code_contracts_and_fixtures_carry_no_retired_taxonomy_identifiers() -> None:
    assert _offenders(_files(CODE_GLOBS), CODE_PATTERNS) == []


def test_active_docs_carry_no_retired_taxonomy_routes_or_parameters() -> None:
    assert _offenders(_files(DOC_GLOBS), DOC_PATTERNS) == []
