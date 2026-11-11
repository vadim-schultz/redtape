"""Search schema migration (chapter 3): extensions, tables and indexes on a migrated database, and the round trip."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator

import pytest
from app.models import Base
from app.models.discovery.enums import enum_values
from app.models.search import EMBEDDING_DIM, WorkTaskStatus
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from test_check_migrations_script import API_ROOT, CURRENT_HEAD, _fresh_database

PARENT = "20261105_retire_legacy_taxonomy"
TABLES = ("candidate_search_text", "candidate_embedding", "embedding_task")
INDEXES = (
    "ix_candidate_search_text_tsv_native",
    "ix_candidate_search_text_tsv_simple",
    "ix_candidate_embedding_hnsw",
    "uq_embedding_task_open",
    "ix_embedding_task_status_priority_created_at",
)


def _alembic(database_url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": str(API_ROOT)}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=API_ROOT, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _scalars(engine: Engine, sql: str) -> list[str]:
    with engine.connect() as connection:
        return list(connection.execute(text(sql)).scalars())


def _index_definitions(engine: Engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(text("select indexname, indexdef from pg_indexes where schemaname = 'public'"))
        return dict(rows.all())


def _present(engine: Engine, kind: str) -> set[str]:
    queries = {
        "tables": "select tablename from pg_tables where schemaname = 'public'",
        "indexes": "select indexname from pg_indexes where schemaname = 'public'",
        "extensions": "select extname from pg_extension",
        "enums": "select typname from pg_type where typtype = 'e'",
    }
    return set(_scalars(engine, queries[kind]))


@pytest.fixture
def migrated() -> Iterator[tuple[str, Engine]]:
    """Yield a throwaway database migrated to head with a connected engine."""
    with _fresh_database() as url:
        _alembic(url, "upgrade", "head")
        engine = create_engine(url)
        try:
            yield url, engine
        finally:
            engine.dispose()


def test_upgrade_creates_the_extensions_tables_indexes_and_enum(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade creates the extensions, the three tables, the GIN and HNSW indexes and the enum."""
    _, engine = migrated

    assert {"vector", "unaccent"} <= _present(engine, "extensions")
    assert set(TABLES) <= _present(engine, "tables")
    assert set(INDEXES) <= _present(engine, "indexes")
    assert "work_task_status" in _present(engine, "enums")
    definitions = _index_definitions(engine)
    assert "USING hnsw (embedding halfvec_cosine_ops) WITH (m='16', ef_construction='64')" in definitions[INDEXES[2]]
    assert "USING gin (tsv_native)" in definitions[INDEXES[0]]
    assert "USING gin (tsv_simple)" in definitions[INDEXES[1]]
    assert (
        "WHERE (status = ANY (ARRAY['pending'::work_task_status, 'claimed'::work_task_status]))"
        in definitions[INDEXES[3]]
    )


def test_model_and_migration_agree_on_dimension_index_names_and_enum_values(migrated: tuple[str, Engine]) -> None:
    """migration · the model and the migration agree on the vector width, the index names and the enum labels."""
    _, engine = migrated

    column_type = _scalars(
        engine,
        "select format_type(atttypid, atttypmod) from pg_attribute "
        "where attrelid = 'candidate_embedding'::regclass and attname = 'embedding'",
    )
    labels = _scalars(
        engine,
        "select enumlabel from pg_enum e join pg_type t on t.oid = e.enumtypid where typname = 'work_task_status' order by e.enumsortorder",
    )
    model_indexes = {index.name for table in TABLES for index in Base.metadata.tables[table].indexes}

    assert column_type == [f"halfvec({EMBEDDING_DIM})"]
    assert labels == enum_values(WorkTaskStatus)
    assert model_indexes == set(INDEXES)


def test_gin_and_hnsw_indexes_serve_the_search_queries(migrated: tuple[str, Engine]) -> None:
    """migration · a tsquery match and a cosine ordering are planned on the GIN and HNSW indexes."""
    _, engine = migrated
    vector = "[" + ",".join(["0.1"] * EMBEDDING_DIM) + "]"
    with engine.begin() as connection:
        connection.execute(text("set local enable_seqscan = off"))
        gin = connection.execute(
            text("explain select 1 from candidate_search_text where tsv_native @@ websearch_to_tsquery('german', 'x')")
        ).scalars()
        hnsw = connection.execute(
            text(f"explain select 1 from candidate_embedding order by embedding <=> '{vector}'::halfvec limit 5")
        ).scalars()
        gin_plan, hnsw_plan = "\n".join(gin), "\n".join(hnsw)

    assert "ix_candidate_search_text_tsv_native" in gin_plan
    assert "ix_candidate_embedding_hnsw" in hnsw_plan


def test_downgrade_drops_tables_indexes_and_enum_but_keeps_the_extensions(migrated: tuple[str, Engine]) -> None:
    """migration · downgrade removes what the revision added and leaves the extensions installed."""
    url, engine = migrated

    _alembic(url, "downgrade", PARENT)

    assert not set(TABLES) & _present(engine, "tables")
    assert not set(INDEXES) & _present(engine, "indexes")
    assert "work_task_status" not in _present(engine, "enums")
    assert {"vector", "unaccent"} <= _present(engine, "extensions")


def test_upgrade_downgrade_upgrade_round_trip_restores_the_schema(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade, downgrade and upgrade again ends with the same tables and indexes."""
    url, engine = migrated
    before = (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums"))

    _alembic(url, "downgrade", "-1")
    _alembic(url, "upgrade", "head")

    assert (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums")) == before
    assert _scalars(engine, "select version_num from alembic_version") == [CURRENT_HEAD]
