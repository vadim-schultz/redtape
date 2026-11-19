"""Locale machine flag migration (AZ14): the column is NOT NULL with default false, and the round trip keeps it."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.models.locale import SupportedLocale
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from test_check_migrations_script import _fresh_database
from test_search_migration import _alembic, _scalars

REVISION = "20261119_task_failure_class"
PARENT = "20261111_snapshot_translation"
COLUMN_SQL = (
    "select is_nullable || ' ' || column_default from information_schema.columns "
    "where table_name = 'supported_locale' and column_name = 'machine_translated'"
)


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


def _flags(engine: Engine) -> list[bool]:
    with engine.connect() as connection:
        return list(connection.execute(text("select machine_translated from supported_locale")).scalars())


def test_upgrade_adds_a_not_null_column_that_defaults_to_false(migrated: tuple[str, Engine]) -> None:
    """migration · upgrade ends on the new revision and adds supported_locale.machine_translated, NOT NULL, default false."""
    _, engine = migrated

    assert _scalars(engine, "select version_num from alembic_version") == [REVISION]
    assert _scalars(engine, COLUMN_SQL) == ["NO false"]
    assert SupportedLocale.__table__.c.machine_translated.nullable is False


def test_downgrade_removes_the_column_and_upgrade_restores_it_with_false(migrated: tuple[str, Engine]) -> None:
    """migration · downgrade removes the column; upgrade restores it and an existing locale reads false."""
    url, engine = migrated
    with engine.begin() as connection:
        connection.execute(
            text(
                "insert into supported_locale (code, name_native, name_english, enabled, completeness_pct) "
                "values ('tr', 'Türkçe', 'Turkish', true, 100)"
            )
        )

    _alembic(url, "downgrade", PARENT)
    assert _scalars(engine, COLUMN_SQL) == []

    _alembic(url, "upgrade", "head")
    assert _scalars(engine, COLUMN_SQL) == ["NO false"]
    assert _flags(engine) == [False]


def test_the_model_and_the_migration_agree_and_alembic_check_is_clean(migrated: tuple[str, Engine]) -> None:
    """migration · after the round trip the schema matches the models and alembic check is clean."""
    url, engine = migrated
    assert _scalars(engine, "select version_num from alembic_version") == [REVISION]

    _alembic(url, "downgrade", PARENT)
    _alembic(url, "upgrade", "head")

    _alembic(url, "check")
