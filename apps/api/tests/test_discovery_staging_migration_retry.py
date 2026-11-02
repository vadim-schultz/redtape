"""Regression tests for idempotent discovery staging migration (Render retry scenario)."""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parent.parent
PARENT_REVISION = "20260929b_suggestion_event"
STAGING_REVISION = "20261012_discovery_staging"
HEAD_REVISION = "20261102_link_table_confidence"
BUDGET_REVISION = "20261028_budget_ledger"

DISCOVERY_SOURCE_ENUM_SQL = "CREATE TYPE discovery_source AS ENUM ('govdata', 'pvog', 'fim', 'leika', 'manual')"


def _psycopg_dsn(database_url: str) -> str:
    """Return a libpq DSN psycopg accepts (not ``postgresql+psycopg``)."""
    return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)


def _postgres_unavailable(exc: psycopg.OperationalError) -> None:
    """Skip or fail when the migration server is unreachable."""
    if os.environ.get("REQUIRE_DB") == "1":
        raise exc
    pytest.skip(f"Postgres unavailable for migration retry tests: {exc}")


@contextmanager
def _fresh_database() -> Iterator[str]:
    """Create a throwaway database on the same server as pytest's Postgres."""
    from app.config import settings

    base = make_url(os.environ.get("DATABASE_URL", settings.database_url))
    name = f"redtape_discovery_mig_{uuid.uuid4().hex[:8]}"
    admin_dsn = _psycopg_dsn(base.set(database="postgres").render_as_string(hide_password=False))
    try:
        admin = psycopg.connect(admin_dsn, autocommit=True)
    except psycopg.OperationalError as exc:
        _postgres_unavailable(exc)
        raise
    with admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    database_url = base.set(database=name).render_as_string(hide_password=False)
    try:
        yield database_url
    finally:
        try:
            with psycopg.connect(admin_dsn, autocommit=True) as cleanup:
                cleanup.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (name,),
                )
                cleanup.execute(f'DROP DATABASE IF EXISTS "{name}"')
        except psycopg.OperationalError:
            pass


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(API_ROOT) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    return subprocess.run(
        ["alembic", *args],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _alembic_version(database_url: str) -> str:
    with psycopg.connect(_psycopg_dsn(database_url)) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    assert row is not None
    return row[0]


def _table_exists(database_url: str, table_name: str) -> bool:
    with psycopg.connect(_psycopg_dsn(database_url)) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = %s",
            (table_name,),
        ).fetchone()
    return row is not None


def test_discovery_staging_upgrade_from_clean_database() -> None:
    """Fresh database reaches head with all discovery staging tables."""
    with _fresh_database() as database_url:
        result = _run_alembic(database_url, "upgrade", "head")
        assert result.returncode == 0, result.stdout + result.stderr
        assert _alembic_version(database_url) == HEAD_REVISION
        assert _table_exists(database_url, "catalogue_service")
        assert _table_exists(database_url, "discovery_event")
        assert _table_exists(database_url, "discovery_document_candidate")
        assert _table_exists(database_url, "discovery_candidate_mention")
        assert _table_exists(database_url, "discovery_budget_ledger")
        assert _table_exists(database_url, "discovery_candidate_edge")


def test_discovery_staging_upgrade_succeeds_when_discovery_source_enum_exists() -> None:
    """Orphan enum from a failed deploy must not block upgrade."""
    with _fresh_database() as database_url:
        parent = _run_alembic(database_url, "upgrade", PARENT_REVISION)
        assert parent.returncode == 0, parent.stdout + parent.stderr

        with psycopg.connect(_psycopg_dsn(database_url), autocommit=True) as conn:
            conn.execute(DISCOVERY_SOURCE_ENUM_SQL)

        head = _run_alembic(database_url, "upgrade", "head")
        assert head.returncode == 0, head.stdout + head.stderr
        assert _alembic_version(database_url) == HEAD_REVISION
        assert _table_exists(database_url, "catalogue_service")


def test_discovery_staging_upgrade_succeeds_when_tables_exist_but_version_is_parent() -> None:
    """Staging schema with stale alembic_version (production stuck state) bumps revision."""
    with _fresh_database() as database_url:
        first = _run_alembic(database_url, "upgrade", "head")
        assert first.returncode == 0, first.stdout + first.stderr

        with psycopg.connect(_psycopg_dsn(database_url)) as conn:
            conn.execute(
                "UPDATE alembic_version SET version_num = %s",
                (STAGING_REVISION,),
            )
            conn.execute(
                "ALTER TABLE discovery_claim DROP CONSTRAINT IF EXISTS uq_discovery_claim_entity_kind_fingerprint"
            )
            conn.execute("ALTER TABLE discovery_claim DROP COLUMN IF EXISTS payload_fingerprint")
            conn.execute("DROP TABLE IF EXISTS discovery_run")
            conn.execute("DROP TABLE IF EXISTS discovery_candidate_edge")
            conn.execute("DROP TYPE IF EXISTS discovery_edge_basis")
            conn.execute("DROP TABLE IF EXISTS discovery_candidate_mention")
            conn.execute("DROP TABLE IF EXISTS discovery_document_candidate")
            conn.execute("DROP TYPE IF EXISTS discovery_candidate_status")
            conn.execute("DROP TYPE IF EXISTS discovery_mention_role")
            conn.execute("ALTER TABLE discovery_task DROP COLUMN IF EXISTS input_key")
            conn.execute("ALTER TABLE discovery_task DROP COLUMN IF EXISTS attempt_count")
            conn.execute("ALTER TABLE discovery_task DROP COLUMN IF EXISTS not_before")
            conn.execute("ALTER TABLE discovery_task DROP COLUMN IF EXISTS artifact_id")
            conn.execute("ALTER TABLE discovery_task DROP COLUMN IF EXISTS result_note")
            conn.execute("DROP TABLE IF EXISTS discovery_budget_ledger")
            conn.execute("DROP TABLE IF EXISTS discovery_artifact")
            conn.execute("DROP TYPE IF EXISTS discovery_artifact_kind")
            # situation-tag-hierarchy chapter 1's own two migrations stack on top of this revision gap;
            # the mention columns vanish with the table dropped above, but document_domain/
            # document_life_situation predate this window and are never dropped, so roll their column back too.
            conn.execute("ALTER TABLE document_domain DROP COLUMN IF EXISTS confidence")
            conn.execute("ALTER TABLE document_life_situation DROP COLUMN IF EXISTS confidence")
            conn.commit()

        assert _alembic_version(database_url) == STAGING_REVISION
        assert _table_exists(database_url, "catalogue_service")

        retry = _run_alembic(database_url, "upgrade", "head")
        assert retry.returncode == 0, retry.stdout + retry.stderr
        assert _alembic_version(database_url) == HEAD_REVISION


def _enum_labels(database_url: str, type_name: str) -> list[str]:
    with psycopg.connect(_psycopg_dsn(database_url)) as conn:
        rows = conn.execute(
            "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = %s",
            (type_name,),
        ).fetchall()
    return [row[0] for row in rows]


def _column_names(database_url: str, table_name: str) -> set[str]:
    with psycopg.connect(_psycopg_dsn(database_url)) as conn:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table_name,)
        ).fetchall()
    return {row[0] for row in rows}


MENTION_COLUMNS = {"condition", "is_optional", "domain_codes", "situation_codes"}


def test_staging_edges_upgrade_adds_labels_columns_and_edge_table() -> None:
    """Head carries the two new enum labels, the mention columns and the edge table."""
    with _fresh_database() as database_url:
        result = _run_alembic(database_url, "upgrade", "head")
        assert result.returncode == 0, result.stdout + result.stderr

        assert "llm_extract" in _enum_labels(database_url, "discovery_task_kind")
        assert "issued" in _enum_labels(database_url, "discovery_mention_role")
        assert _enum_labels(database_url, "discovery_edge_basis") == ["explicit", "derived_single_issued"]
        assert _column_names(database_url, "discovery_candidate_mention") >= MENTION_COLUMNS


def test_staging_edges_downgrade_drops_the_additions_but_keeps_enum_labels() -> None:
    """Round trip: the downgrade removes columns, table and basis enum; labels stay (Postgres cannot drop them).

    ``-3`` walks back past the two situation-tag-hierarchy chapter 1 migrations stacked on top of
    ``staging_edges`` (mention direct-confidence, link-table confidence) to reach this revision's own step.
    """
    with _fresh_database() as database_url:
        assert _run_alembic(database_url, "upgrade", "head").returncode == 0

        down = _run_alembic(database_url, "downgrade", "-3")
        assert down.returncode == 0, down.stdout + down.stderr
        assert _alembic_version(database_url) == BUDGET_REVISION
        assert not _table_exists(database_url, "discovery_candidate_edge")
        assert _enum_labels(database_url, "discovery_edge_basis") == []
        assert not MENTION_COLUMNS & _column_names(database_url, "discovery_candidate_mention")
        assert "llm_extract" in _enum_labels(database_url, "discovery_task_kind")
        assert "issued" in _enum_labels(database_url, "discovery_mention_role")

        up = _run_alembic(database_url, "upgrade", "head")
        assert up.returncode == 0, up.stdout + up.stderr
        assert _alembic_version(database_url) == HEAD_REVISION
