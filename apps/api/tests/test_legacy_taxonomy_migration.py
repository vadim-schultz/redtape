"""Retirement migration gate: legacy tables are dropped only after the archive proves equal and the backfill is clean.

Each test runs the real Alembic chain and the preflight CLI against a disposable database cloned from a template that
is migrated to the pre-retirement revision once per module. Databases are created only on a loopback server, so the
developer ``redtape`` database and any remote host are never touched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
import sqlalchemy as sa
from app.config import settings
from sqlalchemy import Connection, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

API_ROOT = Path(__file__).resolve().parent.parent
CURRENT_HEAD = "20261119_task_failure_class"
PRE_RETIREMENT = "20261104_category_backfill"
PRE_CATEGORY_SCHEMA = "20261104_document_normalized_url"
ARCHIVE = "legacy_taxonomy_archive"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})
RETIRED_TABLES = ("domain", "life_situation_group", "life_situation", "document_domain", "document_life_situation")
MENTION_AXES_TABLE = "discovery_candidate_mention_axes"
MENTION_AXES_SQL = (
    "SELECT id, candidate_id, catalogue_service_id, domain_codes, situation_codes, "
    "direct_domain_confidence, direct_situation_confidence, pvog_leaf_code FROM discovery_candidate_mention"
)
SOURCES: dict[str, str] = {name: f"SELECT * FROM {name}" for name in RETIRED_TABLES} | {
    MENTION_AXES_TABLE: MENTION_AXES_SQL
}
STATE_TABLES = (*RETIRED_TABLES, "discovery_candidate_mention", "category", "document_category")
LATE_MAPPED_CODE = "identity-civil-status"  # a domain code that the crosswalk maps, so the gate does not block
CHECKSUM_SQL = "SELECT count(*), coalesce(md5(string_agg(r::text, chr(31) ORDER BY r::text)), '') FROM ({select}) AS r"

SEED_STATEMENTS = (
    "INSERT INTO jurisdiction (id, kind, code) VALUES (:jurisdiction, 'COUNTRY', 'ZZ')",
    "INSERT INTO document (id, jurisdiction_id, slug) VALUES (:document, :jurisdiction, 'residency')",
    "INSERT INTO domain (id, code) VALUES (:housing, 'housing')",
    "INSERT INTO life_situation_group (id, code) VALUES (:group, 'home-housing')",
    "INSERT INTO life_situation (id, code, group_id) VALUES (:situation, 'moving-house', :group)",
    "INSERT INTO document_domain (document_id, domain_id, confidence) VALUES (:document, :housing, 0.72)",
    "INSERT INTO document_life_situation (document_id, life_situation_id, confidence, pvog_leaf_code) "
    "VALUES (:document, :situation, 0.91, '1050200')",
    "INSERT INTO discovery_document_candidate (id, jurisdiction_id, key) VALUES (:candidate, :jurisdiction, 'residency')",
    "INSERT INTO catalogue_service (id, source, external_id, jurisdiction_id, pipeline_stage) "
    "VALUES (:service, 'manual', 'residency', :jurisdiction, 'T0')",
    "INSERT INTO discovery_candidate_mention (id, candidate_id, catalogue_service_id, role, excerpt, source_field, "
    "extractor, extractor_version, domain_codes, situation_codes, direct_domain_confidence, direct_situation_confidence) "
    "VALUES (:mention, :candidate, :service, 'required', 'Antrag', 'documents', 'llm', '1', "
    "ARRAY['housing'], ARRAY['moving-house'], 0.72, 0.91)",
)


@dataclass(frozen=True, slots=True)
class Seed:
    """Identifiers of the rows that :func:`_seed_legacy` wrote."""

    document_id: uuid.UUID
    mention_id: uuid.UUID


def _server_url() -> URL:
    """Return the test server URL, refusing any host that is not loopback."""
    url = make_url(settings.database_url)
    if url.host not in LOOPBACK_HOSTS:
        raise RuntimeError(f"refusing to create disposable databases on non-loopback host {url.host!r}")
    return url


def _db_url(name: str) -> str:
    return _server_url().set(database=name).render_as_string(hide_password=False)


def _create_database(name: str, template: str | None = None) -> None:
    clause = f' TEMPLATE "{template}"' if template else ""
    admin_dsn = _server_url().set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"{clause}')


def _drop_database(name: str) -> None:
    admin_dsn = _server_url().set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (name,))
        admin.execute(f'DROP DATABASE IF EXISTS "{name}"')


def _environment(database_url: str, **extra: str) -> dict[str, str]:
    return {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": str(API_ROOT), **extra}


def _command(*module_args: str) -> list[str]:
    return [sys.executable, "-m", *module_args]


def _run(database_url: str, *module_args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    """Run a Python module from ``apps/api`` with ``DATABASE_URL`` pinned to ``database_url``."""
    return subprocess.run(
        _command(*module_args),
        cwd=API_ROOT,
        env=_environment(database_url, **extra),
        capture_output=True,
        text=True,
        check=False,
    )


def _start(database_url: str, *module_args: str, **extra: str) -> subprocess.Popen[str]:
    """Start a Python module without waiting, so a test can interleave another connection with it."""
    return subprocess.Popen(
        _command(*module_args),
        cwd=API_ROOT,
        env=_environment(database_url, **extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _alembic(database_url: str, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return _run(database_url, "alembic", *args, **extra)


def _preflight(database_url: str) -> subprocess.CompletedProcess[str]:
    return _run(database_url, "scripts.retirement_preflight")


def _wait_until_waiting_on_a_lock(database_url: str, application_name: str, timeout: float = 60.0) -> None:
    """Block until the named client session is waiting on a lock, so the test knows where the migration is."""
    deadline = time.monotonic() + timeout
    with _connect(database_url) as connection:
        while time.monotonic() < deadline:
            connection.execute(sa.text("SELECT pg_stat_clear_snapshot()"))
            waiting = connection.execute(
                sa.text(
                    "SELECT count(*) FROM pg_stat_activity WHERE application_name = :app AND wait_event_type = 'Lock'"
                ),
                {"app": application_name},
            ).scalar_one()
            if waiting:
                return
            time.sleep(0.1)
    raise AssertionError(f"session {application_name} never waited on a lock")


@contextmanager
def _connect(database_url: str) -> Iterator[Connection]:
    """Yield a connection that commits on exit and releases its pool on exit."""
    engine = create_engine(database_url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            yield connection
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def template_name() -> Iterator[str]:
    """Migrate one template database to the pre-retirement revision for the whole module."""
    name = f"redtape_mig_c3_tpl_{uuid.uuid4().hex[:8]}"
    _create_database(name)
    try:
        result = _alembic(_db_url(name), "upgrade", PRE_RETIREMENT)
        assert result.returncode == 0, result.stderr
        yield name
    finally:
        _drop_database(name)


@pytest.fixture
def pre_retirement_db(template_name: str) -> Iterator[str]:
    """Clone the migrated template into a fresh database and return its URL."""
    name = f"redtape_mig_c3_{uuid.uuid4().hex[:8]}"
    _create_database(name, template=template_name)
    try:
        yield _db_url(name)
    finally:
        _drop_database(name)


def _seed_legacy(database_url: str, *, extra_domain_code: str | None = None) -> Seed:
    """Write one document, one candidate mention and their legacy links, optionally with an unmapped domain code."""
    ids = {name: uuid.uuid4() for name in ("jurisdiction", "document", "housing", "group", "situation")}
    ids |= {"candidate": uuid.uuid4(), "service": uuid.uuid4(), "mention": uuid.uuid4()}
    with _connect(database_url) as connection:
        for statement in SEED_STATEMENTS:
            connection.execute(sa.text(statement), ids)
        if extra_domain_code is not None:
            _seed_extra_domain(connection, ids["document"], extra_domain_code)
    return Seed(document_id=ids["document"], mention_id=ids["mention"])


def _seed_extra_domain(connection: Connection, document_id: uuid.UUID, code: str) -> None:
    domain_id = uuid.uuid4()
    connection.execute(sa.text("INSERT INTO domain (id, code) VALUES (:id, :code)"), {"id": domain_id, "code": code})
    connection.execute(
        sa.text("INSERT INTO document_domain (document_id, domain_id, confidence) VALUES (:document, :domain, 0.5)"),
        {"document": document_id, "domain": domain_id},
    )


def _prepare_unstamped_canonical_schema(database_url: str) -> None:
    """Create the canonical schema, then restore the Alembic stamp before testing adoption."""
    assert _alembic(database_url, "downgrade", PRE_CATEGORY_SCHEMA).returncode == 0
    assert _alembic(database_url, "upgrade", "20261104_category_schema").returncode == 0
    with _connect(database_url) as connection:
        connection.execute(
            sa.text("UPDATE alembic_version SET version_num = :version"),
            {"version": PRE_CATEGORY_SCHEMA},
        )


def _prepare_partial_canonical_schema(database_url: str) -> None:
    """Create one canonical table without its companion tables to test drift rejection."""
    assert _alembic(database_url, "downgrade", PRE_CATEGORY_SCHEMA).returncode == 0
    with _connect(database_url) as connection:
        connection.execute(sa.text("CREATE TABLE category (id uuid PRIMARY KEY)"))


def _checksum(connection: Connection, select_sql: str) -> tuple[int, str]:
    """Return ``(row_count, content_checksum)`` for the rows of ``select_sql``, independent of row order."""
    row = connection.execute(sa.text(CHECKSUM_SQL.format(select=select_sql))).one()
    return int(row[0]), str(row[1])


def _row_count(connection: Connection, table: str) -> int:
    return int(connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one())


def _table_exists(connection: Connection, table: str) -> bool:
    return bool(connection.execute(sa.text("SELECT to_regclass(:name) IS NOT NULL"), {"name": table}).scalar_one())


def _schema_exists(connection: Connection, schema: str) -> bool:
    return bool(
        connection.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = :name)"),
            {"name": schema},
        ).scalar_one()
    )


def _column_shape(connection: Connection, table: str) -> list[tuple[str, str, bool]]:
    return sorted(
        (column["name"], str(column["type"]), column["nullable"])
        for column in sa.inspect(connection).get_columns(table)
    )


def _state(connection: Connection) -> dict[str, object]:
    """Return the row counts and the Alembic revision, to prove that a run changed nothing."""
    version = connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    return {"version": version, "rows": {table: _row_count(connection, table) for table in STATE_TABLES}}


def _evidence(connection: Connection) -> dict[str, tuple[int, str]]:
    rows = connection.execute(
        sa.text(f"SELECT table_name, row_count, archive_checksum FROM {ARCHIVE}.retirement_evidence")
    ).all()
    return {row.table_name: (int(row.row_count), row.archive_checksum) for row in rows}


def _links(connection: Connection, document_id: uuid.UUID) -> dict[str, float]:
    rows = connection.execute(
        sa.text(
            "SELECT category.code, document_category.confidence FROM document_category "
            "JOIN category ON category.id = document_category.category_id WHERE document_category.document_id = :doc"
        ),
        {"doc": document_id},
    ).all()
    return {row.code: row.confidence for row in rows}


def _mention_categories(connection: Connection, mention_id: uuid.UUID) -> tuple[list[str], float]:
    row = connection.execute(
        sa.text("SELECT category_codes, direct_category_confidence FROM discovery_candidate_mention WHERE id = :id"),
        {"id": mention_id},
    ).one()
    return list(row.category_codes), float(row.direct_category_confidence)


def test_upgrade_adopts_an_existing_empty_canonical_schema(pre_retirement_db: str) -> None:
    """Migration · adopt an exact empty canonical schema left behind with an older Alembic stamp."""
    _prepare_unstamped_canonical_schema(pre_retirement_db)

    result = _alembic(pre_retirement_db, "upgrade", "head")

    assert result.returncode == 0, result.stdout + result.stderr
    with _connect(pre_retirement_db) as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM category")).scalar_one() == 34
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == CURRENT_HEAD
        assert not any(_table_exists(connection, table) for table in RETIRED_TABLES)


def test_upgrade_rejects_a_partial_canonical_schema(pre_retirement_db: str) -> None:
    """Migration · reject a partial canonical schema instead of creating through unexplained drift."""
    _prepare_partial_canonical_schema(pre_retirement_db)

    result = _alembic(pre_retirement_db, "upgrade", "head")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "canonical taxonomy schema drift" in output
    with _connect(pre_retirement_db) as connection:
        assert (
            connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == PRE_CATEGORY_SCHEMA
        )
        assert all(_table_exists(connection, table) for table in RETIRED_TABLES)


def test_retirement_archives_verifies_projects_and_drops_the_legacy_tables(pre_retirement_db: str) -> None:
    """Retirement · a seeded database upgrades to head, archives every row with its checksum, and drops the legacy tables."""
    seed = _seed_legacy(pre_retirement_db)
    with _connect(pre_retirement_db) as connection:
        expected = {name: _checksum(connection, select) for name, select in SOURCES.items()}

    result = _alembic(pre_retirement_db, "upgrade", "head")

    assert result.returncode == 0, result.stderr
    with _connect(pre_retirement_db) as connection:
        assert not any(_table_exists(connection, table) for table in RETIRED_TABLES)
        assert {name: _checksum(connection, f"SELECT * FROM {ARCHIVE}.{name}") for name in SOURCES} == expected
        assert _evidence(connection) == expected
        assert _links(connection, seed.document_id) == {"home-and-housing": 0.72, "moving-house": 0.91}
        assert _mention_categories(connection, seed.mention_id) == (["home-and-housing", "moving-house"], 0.91)


def test_unmapped_legacy_code_aborts_and_keeps_the_legacy_tables(pre_retirement_db: str) -> None:
    """Retirement gate · an unmapped legacy code aborts the upgrade, logs the code, and leaves every legacy table."""
    _seed_legacy(pre_retirement_db, extra_domain_code="retired-domain")
    with _connect(pre_retirement_db) as connection:
        before = _state(connection)

    result = _alembic(pre_retirement_db, "upgrade", "head")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert re.search(r"BackfillGateError: .*unmapped", output), output
    assert "retired-domain" in output
    with _connect(pre_retirement_db) as connection:
        assert all(_table_exists(connection, table) for table in RETIRED_TABLES)
        assert not _schema_exists(connection, ARCHIVE)
        assert _state(connection) == before


def test_archive_checksum_mismatch_aborts_and_keeps_the_legacy_tables(pre_retirement_db: str) -> None:
    """Retirement verify · a stale archive copy with the same row count aborts the upgrade and keeps every legacy table."""
    _seed_legacy(pre_retirement_db)
    with _connect(pre_retirement_db) as connection:
        connection.execute(sa.text(f"CREATE SCHEMA {ARCHIVE}"))
        connection.execute(sa.text(f"CREATE TABLE {ARCHIVE}.domain AS SELECT * FROM domain"))
        connection.execute(sa.text(f"UPDATE {ARCHIVE}.domain SET code = 'tampered'"))
        before = _state(connection)

    result = _alembic(pre_retirement_db, "upgrade", "head")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert re.search(r"ArchiveMismatchError: .*domain.*checksum", output), output
    with _connect(pre_retirement_db) as connection:
        assert all(_table_exists(connection, table) for table in RETIRED_TABLES)
        assert connection.execute(sa.text(f"SELECT code FROM {ARCHIVE}.domain")).scalars().all() == ["tampered"]
        assert _state(connection) == before


def test_downgrade_recreates_the_empty_legacy_shape_and_keeps_the_archive(pre_retirement_db: str) -> None:
    """Downgrade · the retirement revision restores the empty pre-retirement shape and leaves the archive untouched."""
    shaped = (*RETIRED_TABLES, "discovery_candidate_mention")
    with _connect(pre_retirement_db) as connection:
        shape = {table: _column_shape(connection, table) for table in shaped}
    _seed_legacy(pre_retirement_db)
    assert _alembic(pre_retirement_db, "upgrade", "head").returncode == 0
    with _connect(pre_retirement_db) as connection:
        archived = {name: _checksum(connection, f"SELECT * FROM {ARCHIVE}.{name}") for name in SOURCES}

    result = _alembic(pre_retirement_db, "downgrade", PRE_RETIREMENT)

    assert result.returncode == 0, result.stderr
    with _connect(pre_retirement_db) as connection:
        assert {table: _column_shape(connection, table) for table in shaped} == shape
        assert [_row_count(connection, table) for table in RETIRED_TABLES] == [0] * len(RETIRED_TABLES)
        assert {name: _checksum(connection, f"SELECT * FROM {ARCHIVE}.{name}") for name in SOURCES} == archived


def test_a_link_committed_during_the_migration_is_archived_not_dropped(pre_retirement_db: str) -> None:
    """Retirement concurrency · a link committed while the migration waits is archived, never dropped unarchived."""
    seed = _seed_legacy(pre_retirement_db)
    application = f"c3-race-{uuid.uuid4().hex[:8]}"
    engine = create_engine(pre_retirement_db, poolclass=NullPool)
    writer = engine.connect()
    transaction = writer.begin()
    try:
        _seed_extra_domain(writer, seed.document_id, LATE_MAPPED_CODE)
        migration = _start(pre_retirement_db, "alembic", "upgrade", "head", PGAPPNAME=application)
        _wait_until_waiting_on_a_lock(pre_retirement_db, application)
        transaction.commit()
    finally:
        writer.close()
        engine.dispose()

    stdout, stderr = migration.communicate(timeout=120)

    assert migration.returncode == 0, stdout + stderr
    with _connect(pre_retirement_db) as connection:
        assert connection.execute(sa.text(f"SELECT code FROM {ARCHIVE}.domain ORDER BY code")).scalars().all() == [
            "housing",
            LATE_MAPPED_CODE,
        ]
        assert _row_count(connection, f"{ARCHIVE}.document_domain") == 2


def test_a_writer_that_never_commits_aborts_the_migration_before_any_drop(pre_retirement_db: str) -> None:
    """Retirement concurrency · a writer holding a retired table past the lock timeout aborts the migration."""
    seed = _seed_legacy(pre_retirement_db)
    engine = create_engine(pre_retirement_db, poolclass=NullPool)
    writer = engine.connect()
    transaction = writer.begin()
    try:
        _seed_extra_domain(writer, seed.document_id, LATE_MAPPED_CODE)
        with _connect(pre_retirement_db) as connection:
            before = _state(connection)
        result = _alembic(pre_retirement_db, "upgrade", "head", PGOPTIONS="-c lock_timeout=1000")
    finally:
        transaction.rollback()
        writer.close()
        engine.dispose()

    assert result.returncode != 0
    assert "lock timeout" in (result.stdout + result.stderr).lower()
    with _connect(pre_retirement_db) as connection:
        assert all(_table_exists(connection, table) for table in RETIRED_TABLES)
        assert not _schema_exists(connection, ARCHIVE)
        assert _state(connection) == before


def test_preflight_reports_counts_checksums_and_dry_run_without_writing(pre_retirement_db: str) -> None:
    """Preflight · reports row counts, checksums, mention axes and the dry-run gate inputs, and writes nothing."""
    _seed_legacy(pre_retirement_db, extra_domain_code="retired-domain")
    with _connect(pre_retirement_db) as connection:
        before = _state(connection)
        expected = {name: _checksum(connection, select) for name, select in SOURCES.items()}

    result = _preflight(pre_retirement_db)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["read_only"] is True
    assert report["tables"] == {
        name: {"row_count": count, "checksum": checksum} for name, (count, checksum) in expected.items()
    }
    assert report["mention_axes"] == {
        "mentions": 1,
        "with_domain_codes": 1,
        "with_situation_codes": 1,
        "unknown_codes": [],
    }
    dry_run = report["backfill_dry_run"]
    assert dry_run["dry_run"] is True
    assert (dry_run["unmapped_rows"], dry_run["ambiguous_rows"], dry_run["conflict_rows"]) == (1, 0, 0)
    assert "null_confidence_rows" in dry_run
    with _connect(pre_retirement_db) as connection:
        assert _state(connection) == before


def test_preflight_refuses_a_database_without_legacy_tables(pre_retirement_db: str) -> None:
    """Preflight · a database that is already retired fails loudly and prints no report."""
    assert _alembic(pre_retirement_db, "upgrade", "head").returncode == 0

    result = _preflight(pre_retirement_db)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "missing" in result.stderr.lower()
    assert "domain" in result.stderr
