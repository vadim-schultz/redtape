"""Translation schema migration (chapter 13): tables, indexes, enum and the round trip after the search schema."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.models import Base
from app.models.discovery.enums import enum_values
from app.models.translation import TranslationSource
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from test_check_migrations_script import CURRENT_HEAD, _fresh_database
from test_search_migration import _alembic, _index_definitions, _present, _scalars

PARENT = "20261110_search_schema"
TABLES = ("candidate_translation", "translation_task")
INDEXES = ("uq_translation_task_open", "ix_translation_task_status_priority_created_at")


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


def test_upgrade_creates_both_tables_the_open_task_index_and_the_source_enum(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade creates the index table, the task table, their indexes and the translation_source enum."""
    _, engine = migrated

    assert set(TABLES) <= _present(engine, "tables")
    assert set(INDEXES) <= _present(engine, "indexes")
    assert "translation_source" in _present(engine, "enums")
    definition = _index_definitions(engine)[INDEXES[0]]
    assert "UNIQUE INDEX" in definition and "(candidate_id, locale)" in definition
    assert "WHERE (status = ANY (ARRAY['pending'::work_task_status, 'claimed'::work_task_status]))" in definition


def test_upgrade_ends_on_the_head_revision_and_keeps_the_search_schema_beneath_the_translation_tables(
    migrated: tuple[str, Engine],
) -> None:
    """migration · upgrade ends on the head revision, which keeps the search schema the translation tables build on."""
    _, engine = migrated

    assert _scalars(engine, "select version_num from alembic_version") == [CURRENT_HEAD]
    assert "embedding_task" in _present(engine, "tables")


def test_model_and_migration_agree_on_columns_index_names_and_enum_values(migrated: tuple[str, Engine]) -> None:
    """migration · the model and the migration agree on the column names, index names and enum labels."""
    _, engine = migrated

    labels = _scalars(
        engine,
        "select enumlabel from pg_enum e join pg_type t on t.oid = e.enumtypid "
        "where typname = 'translation_source' order by e.enumsortorder",
    )
    columns = _scalars(
        engine,
        "select column_name from information_schema.columns where table_name = 'candidate_translation' order by ordinal_position",
    )
    model_columns = [column.name for column in Base.metadata.tables["candidate_translation"].columns]

    assert labels == enum_values(TranslationSource)
    assert sorted(columns) == sorted(model_columns)
    assert {index.name for index in Base.metadata.tables["translation_task"].indexes} == set(INDEXES)


def test_downgrade_drops_what_the_revision_added_and_keeps_the_search_schema(migrated: tuple[str, Engine]) -> None:
    """migration · downgrade removes the tables and the enum and leaves chapter 3's tables and work_task_status."""
    url, engine = migrated

    _alembic(url, "downgrade", PARENT)

    assert not set(TABLES) & _present(engine, "tables")
    assert "translation_source" not in _present(engine, "enums")
    assert {"embedding_task", "candidate_embedding"} <= _present(engine, "tables")
    assert "work_task_status" in _present(engine, "enums")


def test_upgrade_downgrade_upgrade_round_trip_restores_the_schema(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade, downgrade and upgrade again ends with the same tables, indexes and enums."""
    url, engine = migrated
    before = (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums"))

    _alembic(url, "downgrade", "-1")
    _alembic(url, "upgrade", "head")

    assert (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums")) == before
    assert _scalars(engine, "select version_num from alembic_version") == [CURRENT_HEAD]
