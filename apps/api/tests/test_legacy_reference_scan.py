"""Chapter C10 reference scan: retired taxonomy identifiers stay out of code, contracts, fixtures and active docs.

Every in-scope line that names a retired identifier fails the scan unless one :class:`LineAllowance` covers it.
An allowance names a file, a regex that must match the line, and a reason. An allowance whose file is missing,
or that covers no retired line, is stale and fails the scan. ``.plans/`` records history and is out of scope.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

CODE_ROOTS = ("apps/api", "apps/discovery-ingest", "apps/web/src")
DOC_ROOTS = ("docs",)
README_GLOB = "apps/*/README.md"
TEXT_SUFFIXES = frozenset(
    {
        ".example",
        ".html",
        ".ini",
        ".json",
        ".lock",
        ".mako",
        ".md",
        ".py",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
    }
)
SKIPPED_DIRECTORIES = frozenset({".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})

RETIRED_PATTERNS = (
    r"api/v1/(matrix|domains|life-situations|life-situation-groups)\b",
    r"\bfetch(Domains|LifeSituations|LifeSituationGroups|Matrix)\b",
    r"\buse(Domains|LifeSituations|LifeSituationGroups)Query\b",
    r"\bdocument_domain\b|\bdocument_life_situation\b",
    r"\blife_situation_group\b|\bLifeSituationGroup\b|\bLifeSituation\b",
    r"\bdomain_codes\b|\bsituation_codes\b",
    r"\bdirect_(domain|situation)_confidence\b",
    r"\bMatrix(Response|Cell)\b|\bget_matrix\b|\bmatrix_counts\b",
    r"filter\[(domain|situation|group)\]",
    r"\bfilter_(domain|situation|group)\b",
    r"[?&](domain|situation|group)=",
)

REASON_HISTORICAL_REVISION = "Frozen Alembic revision: it records the legacy schema that it created, changed or dropped, and history is not rewritten."
REASON_RETIREMENT_REVISION = (
    "Retirement revision 20261105: it names the legacy mention columns that the archive copies and the drop removes."
)
REASON_RETIREMENT_DOWNGRADE = "Retirement revision 20261105 downgrade: it recreates the empty legacy schema, and the archive keeps the only copy of the rows."
REASON_REPLAY_PROJECTION = (
    "Replay projection for the retirement migration: it maps the legacy mention axes through the frozen crosswalk."
)
REASON_ARCHIVE_STEP = (
    "Archive step: it copies the retired relations into the archive schema and compares each copy with its source."
)
REASON_FROZEN_TABLE_SHAPE = "Frozen shape of a retired table, read only by historical revisions and the archive step. No runtime code imports it."
REASON_REJECTION_GUARD = "Rejection guard: it names a retired field so that a request carrying it is refused by name."
REASON_NEGATIVE_CONTRACT = "Negative contract: it asserts that a retired name is refused, absent, or not advertised."
REASON_NEGATIVE_INPUT = "Negative input: it is a retired field that a test expects to be refused by name."
REASON_C3_GATE = (
    "C3 retirement gate: it builds or reads the legacy tables to prove the archive, the backfill and the drop."
)
REASON_HISTORICAL_TEST = (
    "Historical migration test: it rolls the pre-C9 link tables and group tier back to reach an older revision."
)
REASON_RETIRED_MODULE = "Retired pre-C9 test module, skipped at module level. Deleting it is a follow-up, outside C10."
REASON_SCANNER_VOCABULARY = (
    "Scanner fixture: a retired identifier written on purpose so the planted-identifier test has a line to find."
)


@dataclass(frozen=True)
class LineAllowance:
    """One reasoned exception: lines of ``path`` that ``pattern`` matches may keep a retired identifier."""

    path: str
    pattern: str
    reason: str

    def __post_init__(self) -> None:
        """Refuse an allowance that has no reason."""
        if not self.reason.strip():
            raise ValueError(f"allowance for {self.path} needs a reason")


def _allow(path: str, reason: str, *patterns: str) -> tuple[LineAllowance, ...]:
    return tuple(LineAllowance(path, pattern, reason) for pattern in patterns)


ALLOWANCES: tuple[LineAllowance, ...] = (
    # Frozen Alembic revisions: history is not rewritten.
    *_allow(
        "apps/api/alembic/versions/20260625_taxonomy.py",
        REASON_HISTORICAL_REVISION,
        r'_link_table\("document_(domain|life_situation)"',
        r'op\.drop_table\("document_(life_situation|domain)"\)',
    ),
    *_allow(
        "apps/api/alembic/versions/20261029_discovery_staging_edges.py",
        REASON_HISTORICAL_REVISION,
        r"``(domain|situation)_codes`` and ``",
        r'sa\.Column\("(domain|situation)_codes"',
        r'for column in \("(situation|domain)_codes"',
    ),
    *_allow(
        "apps/api/alembic/versions/20261102_life_situation_group.py",
        REASON_HISTORICAL_REVISION,
        r'^"""Add the life_situation_(group) taxonomy tier',
        r'"life_situation_(group)",',
        r'sa\.ForeignKey\("life_situation_(group)\.id"\)',
        r'op\.drop_table\("life_situation_(group)"\)',
    ),
    *_allow(
        "apps/api/alembic/versions/20261102_link_table_confidence.py",
        REASON_HISTORICAL_REVISION,
        r'^"""Add the confidence column to document_(domain) and document_(life_situation)\.',
        r'LINK_TABLES = \("document_(domain|life_situation)"',
    ),
    *_allow(
        "apps/api/alembic/versions/20261102_mention_confidence.py",
        REASON_HISTORICAL_REVISION,
        r'COLUMNS = \("direct_(domain|situation)_confidence"',
    ),
    *_allow(
        "apps/api/alembic/versions/20261102_pvog_leaf_code.py",
        REASON_HISTORICAL_REVISION,
        r"and document_(life_situation)\.",
        r"``document_(life_situation)\.pvog_leaf_code``",
        r"Not added to ``document_(domain)``",
        r'op\.(add|drop)_column\("document_(life_situation)"',
    ),
    *_allow(
        "apps/api/alembic/versions/20261102_remove_seeded_documents.py",
        REASON_HISTORICAL_REVISION,
        r"``document_(domain)`` and ``document_(life_situation)``",
    ),
    # Retirement revision: archives, verifies and drops the legacy taxonomy, and its downgrade recreates it empty.
    *_allow(
        "apps/api/alembic/versions/20261105_retire_legacy_taxonomy.py",
        REASON_RETIREMENT_REVISION,
        r"^LEGACY_MENTION_COLUMNS = ",
    ),
    *_allow(
        "apps/api/alembic/versions/20261105_retire_legacy_taxonomy.py",
        REASON_RETIREMENT_DOWNGRADE,
        r'op\.add_column\(MENTION_TABLE, sa\.Column\("(domain|situation)_codes"',
        r'op\.add_column\(MENTION_TABLE, sa\.Column\("direct_(domain|situation)_confidence"',
        r'"life_situation_(group)",',
        r'sa\.ForeignKey\("life_situation_(group)\.id"\)',
        r'"document_(domain|life_situation)",',
    ),
    # Guards that refuse retired fields by name.
    *_allow(
        "apps/api/app/shared/retired_taxonomy.py",
        REASON_REJECTION_GUARD,
        r'"(domain|situation)_codes",',
        r'"direct_(domain|situation)_confidence",',
        r"as ``filter\[domain\]``",
    ),
    *_allow(
        "apps/discovery-ingest/discovery_ingest/mentions.py",
        REASON_REJECTION_GUARD,
        r'^    \{"(domain|situation)_codes", ',
    ),
    *_allow(
        "apps/discovery-ingest/discovery_ingest/extract/llm/schema.py",
        REASON_REJECTION_GUARD,
        r'\{"(domain|situation)_codes", "(domain|situation)_codes"\}',
    ),
    # Replay and archive code that reads the legacy axes for the retirement migration.
    *_allow(
        "apps/api/scripts/category_mention_projection.py",
        REASON_REPLAY_PROJECTION,
        r'sa\.column\("(domain|situation)_codes"',
        r'sa\.column\("direct_(domain|situation)_confidence"',
        r"^    (domain|situation)_codes: Sequence",
        r"^    direct_(domain|situation)_confidence: float",
        r'"domain", (domain|situation)_codes or',
        r"_strongest\(\(direct_(domain|situation)_confidence",
        r"=row\.(domain|situation)_codes,",
        r"=row\.direct_(domain|situation)_confidence,",
        r"MENTION_TABLE\.c\.(domain|situation)_codes",
        r"MENTION_TABLE\.c\.direct_(domain|situation)_confidence",
    ),
    *_allow(
        "apps/api/scripts/legacy_taxonomy_archive.py",
        REASON_ARCHIVE_STEP,
        r'"(document_(domain|life_situation)|life_situation_(group))",',
        r"catalogue_service_id, (domain|situation)_codes, ",
        r"direct_(domain|situation)_confidence, direct_\w+_confidence, pvog_leaf_code",
        r"SELECT (domain|situation)_codes, ",
        r"with_(domain|situation)_codes=sum\(row\.",
        r"=row\.(domain|situation)_codes,",
        r"=row\.direct_(domain|situation)_confidence,",
    ),
    *_allow(
        "apps/api/scripts/seed_data/legacy_tables.py",
        REASON_FROZEN_TABLE_SHAPE,
        r'"(document_(domain|life_situation)|life_situation_(group))",',
        r'sa\.Column\("(domain|situation)_codes"',
        r'sa\.Column\("direct_(domain|situation)_confidence"',
    ),
    # Ingest code and tests: rejection and negative cases only.
    *_allow(
        "apps/discovery-ingest/tests/test_c4_category_contract.py",
        REASON_NEGATIVE_CONTRACT,
        r'assert "(domain|situation)_codes" not in schema\["properties"\]',
    ),
    *_allow(
        "apps/discovery-ingest/tests/test_c4_category_contract.py",
        REASON_NEGATIVE_INPUT,
        r'^ +"(domain|situation)_codes": \[',
    ),
    *_allow(
        "apps/discovery-ingest/tests/test_category_codes_only.py",
        REASON_NEGATIVE_INPUT,
        r"The retired ``(domain|situation)_codes``",
        r'^    "(domain|situation)_codes": \[',
        r'^    "direct_(domain|situation)_confidence": ',
        r'LEGACY_LABEL_FIELDS = \("(domain|situation)_codes"',
    ),
    # Web contract test: the forbidden-field list.
    *_allow(
        "apps/web/src/test/contract/contract.test.ts",
        REASON_NEGATIVE_CONTRACT,
        r'^  "(domain|situation)_codes",',
        r'^  "direct_(domain|situation)_confidence",',
    ),
    # API tests: C3 gate, negative contracts, historical fixtures and retired skipped modules.
    *_allow(
        "apps/api/tests/test_legacy_taxonomy_migration.py",
        REASON_C3_GATE,
        r"^RETIRED_TABLES = \(",
        r"catalogue_service_id, (domain|situation)_codes, ",
        r"direct_(domain|situation)_confidence, direct_\w+_confidence, pvog_leaf_code",
        r"INSERT INTO life_situation_(group) ",
        r"INSERT INTO document_(domain) ",
        r"INSERT INTO document_(life_situation) ",
        r"extractor_version, (domain|situation)_codes, ",
        r"\{ARCHIVE\}\.document_(domain)",
    ),
    *_allow(
        "apps/api/tests/test_legacy_taxonomy_retirement.py",
        REASON_NEGATIVE_CONTRACT,
        r'"/api/v1/(domains|life-situations|life-situation-groups|matrix)",',
        r'^    "filter\[(domain|group|situation)\]",',
        r"^RETIRED_CANDIDATE_FILTERS = ",
        r"_mention_payload\((domain|situation)_codes=",
        r'"(domain)_codes": \["housing"\]\}\)',
    ),
    *_allow(
        "apps/api/tests/test_c4_category_contract.py",
        REASON_NEGATIVE_CONTRACT,
        r'parametrize\("field", \("(domain|situation)_codes", "(domain|situation)_codes"\)\)',
    ),
    *_allow(
        "apps/api/tests/test_taxonomy_api.py",
        REASON_NEGATIVE_CONTRACT,
        r'"/api/v1/(domains|life-situations|life-situation-groups|matrix)",',
    ),
    *_allow(
        "apps/api/tests/test_documents_filter.py",
        REASON_NEGATIVE_CONTRACT,
        r'"param", \("domain", "group", "situation", ',
    ),
    *_allow(
        "apps/api/tests/test_suggestion_payload.py",
        REASON_NEGATIVE_CONTRACT,
        r'isdisjoint\(\{"(domain|situation)_codes"',
    ),
    *_allow(
        "apps/api/tests/test_discovery_staging_migration_retry.py",
        REASON_HISTORICAL_TEST,
        r"document_(domain)/document_(life_situation)/life_situation predate",
        r"ALTER TABLE document_(domain|life_situation) DROP COLUMN",
        r"DROP TABLE IF EXISTS life_situation_(group)",
        r"link-table confidence, life_situation_(group) and pvog_leaf_code",
    ),
    *_allow(
        "apps/api/tests/test_remove_seeded_documents_migration.py",
        REASON_RETIRED_MODULE,
        r"document_(domain)\b",
    ),
    *_allow(
        "apps/api/tests/test_document_repository.py",
        REASON_RETIRED_MODULE,
        r"type\[Life(Situation)\]",
        r"_term\(db_session, Life(Situation),",
        r"select\(document_(life_situation)\.c\.pvog_leaf_code\)",
    ),
    *_allow(
        "apps/api/tests/test_document_service.py",
        REASON_RETIRED_MODULE,
        r"(domain|situation)_codes=\[",
        r"select\(document_(life_situation)\.c\.pvog_leaf_code\)",
    ),
    *_allow(
        "apps/api/tests/test_legacy_reference_scan.py",
        REASON_SCANNER_VOCABULARY,
        r"^PLANTED_LINE = ",
    ),
)


def _walk(root: Path) -> Iterator[Path]:
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIPPED_DIRECTORIES]
        yield from (Path(directory, name) for name in filenames if Path(name).suffix in TEXT_SUFFIXES)


def _files(roots: Iterable[str]) -> list[Path]:
    return sorted({path for root in roots for path in _walk(REPO_ROOT / root)})


def _doc_files() -> list[Path]:
    return sorted({*_files(DOC_ROOTS), *REPO_ROOT.glob(README_GLOB)})


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _compile(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in patterns]


def _is_hit(line: str, retired: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(line) for pattern in retired)


def _matches(allowance: LineAllowance, line: str) -> bool:
    return re.search(allowance.pattern, line) is not None


def _is_allowed(line: str, allowances: Iterable[LineAllowance]) -> bool:
    return any(_matches(allowance, line) for allowance in allowances)


def _file_offenders(path: Path, retired: list[re.Pattern[str]], allowances: list[LineAllowance]) -> list[str]:
    relative = _relative(path)
    own = [allowance for allowance in allowances if allowance.path == relative]
    lines = _read_lines(path)
    return [
        f"{relative}:{number}: {line.strip()[:120]}"
        for number, line in enumerate(lines, start=1)
        if _is_hit(line, retired) and not _is_allowed(line, own)
    ]


def _offenders(paths: Iterable[Path], patterns: tuple[str, ...], allowances: Iterable[LineAllowance]) -> list[str]:
    retired = _compile(patterns)
    allowed = list(allowances)
    return [offense for path in paths for offense in _file_offenders(path, retired, allowed)]


def _stale_problem(allowance: LineAllowance, retired: list[re.Pattern[str]]) -> str | None:
    return _missing_file_problem(allowance) or _uncovered_problem(allowance, retired)


def _missing_file_problem(allowance: LineAllowance) -> str | None:
    if (REPO_ROOT / allowance.path).is_file():
        return None
    return f"{allowance.path}: allowance names a missing file"


def _uncovered_problem(allowance: LineAllowance, retired: list[re.Pattern[str]]) -> str | None:
    lines = _read_lines(REPO_ROOT / allowance.path)
    if any(_is_hit(line, retired) and _matches(allowance, line) for line in lines):
        return None
    return f"{allowance.path}: allowance {allowance.pattern!r} covers no retired line"


def _stale_problems(allowances: Iterable[LineAllowance]) -> list[str]:
    retired = _compile(RETIRED_PATTERNS)
    return [problem for allowance in allowances if (problem := _stale_problem(allowance, retired))]


def test_runtime_code_contracts_and_fixtures_carry_no_retired_taxonomy_identifiers() -> None:
    assert _offenders(_files(CODE_ROOTS), RETIRED_PATTERNS, ALLOWANCES) == []


def test_active_docs_carry_no_retired_taxonomy_routes_or_parameters() -> None:
    assert _offenders(_doc_files(), RETIRED_PATTERNS, ALLOWANCES) == []


def test_every_allowance_names_an_existing_file_and_a_live_hit() -> None:
    assert _stale_problems(ALLOWANCES) == []


def test_allowance_naming_a_missing_file_is_reported_as_stale() -> None:
    ghost = LineAllowance("apps/api/tests/test_missing_c10.py", r"(domain)_codes", "reason")

    assert _stale_problems([ghost]) == ["apps/api/tests/test_missing_c10.py: allowance names a missing file"]


def test_allowance_covering_no_retired_line_is_reported_as_stale() -> None:
    stale = LineAllowance("apps/api/tests/test_document_service.py", r"no_such_identifier", "reason")

    assert _stale_problems([stale]) == [
        "apps/api/tests/test_document_service.py: allowance 'no_such_identifier' covers no retired line"
    ]


def test_allowance_without_a_reason_is_rejected() -> None:
    with pytest.raises(ValueError, match="reason"):
        LineAllowance("apps/api/tests/test_document_service.py", r"(domain)_codes", "   ")


PROBE_PATH = "apps/discovery-ingest/discovery_ingest/_c10_scan_probe.py"
PLANTED_LINE = 'RETIRED = "domain_codes"'


@pytest.fixture
def planted_legacy_identifier() -> Iterator[None]:
    probe = REPO_ROOT / PROBE_PATH
    probe.write_text(
        f'"""Temporary reference-scan probe; removed after the test."""\n{PLANTED_LINE}\n', encoding="utf-8"
    )
    try:
        yield
    finally:
        probe.unlink(missing_ok=True)


def test_planted_legacy_identifier_fails_the_scan_with_file_and_line(planted_legacy_identifier: None) -> None:
    offenders = _offenders(_files(CODE_ROOTS), RETIRED_PATTERNS, ALLOWANCES)

    assert f"{PROBE_PATH}:2: {PLANTED_LINE}" in offenders
