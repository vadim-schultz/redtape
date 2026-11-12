"""Snapshot translation schema migration (chapter 07): tables, indexes, the storage check and the round trip."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.models import Base
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from test_check_migrations_script import _fresh_database
from test_search_migration import _alembic, _index_definitions, _present, _scalars
from test_snapshot_models import catalogue_row

REVISION = "20261111_snapshot_translation"
PARENT = "20261111_translation_schema"
TABLES = ("snapshot_translation", "snapshot_translation_task")
INDEXES = ("uq_snapshot_translation_task_open", "ix_snapshot_translation_task_status_priority_created_at")
CHECK = "ck_snapshot_translation_storage_xor_skip"
HASH = "a" * 64


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


def test_upgrade_creates_both_tables_the_open_task_index_and_the_storage_check(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade creates the index table, the task table, the open-task index and the storage check."""
    _, engine = migrated

    assert set(TABLES) <= _present(engine, "tables")
    assert set(INDEXES) <= _present(engine, "indexes")
    assert _scalars(engine, f"select conname from pg_constraint where conname = '{CHECK}'") == [CHECK]
    definition = _index_definitions(engine)[INDEXES[0]]
    assert "UNIQUE INDEX" in definition and "(catalogue_service_id, locale)" in definition
    assert "WHERE (status = ANY (ARRAY['pending'::work_task_status, 'claimed'::work_task_status]))" in definition


def test_upgrade_ends_on_the_snapshot_revision_and_keeps_the_translation_schema(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade ends on the new revision and keeps the translation tables and the status enum beneath it."""
    _, engine = migrated

    assert _scalars(engine, "select version_num from alembic_version") == [REVISION]
    assert {"candidate_translation", "translation_task"} <= _present(engine, "tables")
    assert "work_task_status" in _present(engine, "enums")


def test_model_and_migration_agree_on_columns_and_index_names(migrated: tuple[str, Engine]) -> None:
    """migration · the model and the migration agree on the columns of both tables and the open-task index name."""
    _, engine = migrated

    for table in TABLES:
        columns = _scalars(
            engine,
            f"select column_name from information_schema.columns where table_name = '{table}'",
        )
        assert sorted(columns) == sorted(column.name for column in Base.metadata.tables[table].columns)
    assert {index.name for index in Base.metadata.tables["snapshot_translation_task"].indexes} == set(INDEXES)


def test_downgrade_drops_both_tables_and_keeps_the_translation_schema(migrated: tuple[str, Engine]) -> None:
    """migration · downgrade removes the two snapshot tables and leaves the translation tables in place."""
    url, engine = migrated

    _alembic(url, "downgrade", PARENT)

    assert not set(TABLES) & _present(engine, "tables")
    assert not set(INDEXES) & _present(engine, "indexes")
    assert {"candidate_translation", "translation_task"} <= _present(engine, "tables")


def test_upgrade_downgrade_upgrade_round_trip_restores_the_schema_and_alembic_check_is_clean(
    migrated: tuple[str, Engine],
) -> None:
    """migration · upgrade, downgrade and upgrade again round-trip to the same schema, and alembic check is clean."""
    url, engine = migrated
    before = (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums"))

    _alembic(url, "check")
    _alembic(url, "downgrade", "-1")
    _alembic(url, "upgrade", "head")

    assert (_present(engine, "tables"), _present(engine, "indexes"), _present(engine, "enums")) == before
    assert _scalars(engine, "select version_num from alembic_version") == [REVISION]
    _alembic(url, "check")


def test_the_partial_unique_index_allows_one_open_task_per_catalogue_row_and_locale_and_a_new_one_after_completion(
    migrated: tuple[str, Engine],
) -> None:
    """migration · one open task per (catalogue row, locale); once it completes, a new open task is allowed."""
    _, engine = migrated
    with Session(engine) as session:
        catalogue = catalogue_row(session)
        first = SnapshotTranslationTask(catalogue_service_id=catalogue.id, locale="en", source_hash=HASH)
        session.add(first)
        session.commit()

        session.add(SnapshotTranslationTask(catalogue_service_id=catalogue.id, locale="en", source_hash=HASH))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        first = session.get(SnapshotTranslationTask, first.id)
        assert first is not None
        first.status = WorkTaskStatus.COMPLETED
        session.add(SnapshotTranslationTask(catalogue_service_id=catalogue.id, locale="en", source_hash=HASH))
        session.commit()

        statuses = sorted(session.scalars(select(SnapshotTranslationTask.status)).all())

    assert statuses == sorted([WorkTaskStatus.COMPLETED, WorkTaskStatus.PENDING])
