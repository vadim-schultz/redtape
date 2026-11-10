from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest
from app.config import settings
from app.db import engine as db_engine
from app.models import Base
from sqlalchemy import event, text
from sqlalchemy.orm import Session

# pysqlite intercepts BEGIN/SAVEPOINT handling in ways that break nested
# transactions unless its own implicit transaction control is disabled.
# No-op against Postgres/other dialects.
if db_engine.dialect.name == "sqlite":

    @event.listens_for(db_engine, "connect")
    def _sqlite_disable_pysqlite_txn_control(dbapi_connection, connection_record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(db_engine, "begin")
    def _sqlite_emit_explicit_begin(conn) -> None:
        conn.exec_driver_sql("BEGIN")


@pytest.fixture(scope="function")
def deterministic_uuid_namespace() -> uuid.UUID:
    """
    Deterministic namespace for stable UUID generation in tests.

    Using a fixed namespace ensures repeatable UUIDs within a test.
    """

    return uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit")


def _require_db() -> bool:
    return os.environ.get("REQUIRE_DB") == "1"


REQUIRED_EXTENSIONS = ("vector", "unaccent")
"""Extensions the models and queries rely on; Alembic creates the same ones for real databases."""


def _create_extensions() -> None:
    """Install the extensions before `create_all`, so `Vector` columns and `unaccent` calls work in unit tests."""
    with db_engine.begin() as connection:
        for name in REQUIRED_EXTENSIONS:
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {name}"))


def _try_create_schema() -> None:
    # If the DB is unavailable, REQUIRE_DB=1 (always set in CI) fails loud;
    # otherwise we skip integration tests (common for a contributor without Docker).
    _create_extensions()
    Base.metadata.create_all(db_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provide a SQLAlchemy session wrapped in an outer transaction that is always
    rolled back at teardown, so tests never leak state to each other.

    Test code may call session.commit() freely: with
    join_transaction_mode="create_savepoint", commit() releases/restarts a
    SAVEPOINT rather than ending the real transaction, so the final rollback
    still discards everything. Integration tests will be skipped if the
    configured database is unreachable.
    """

    try:
        _try_create_schema()
    except Exception as e:
        if _require_db():
            raise
        pytest.skip(f"Database unavailable for tests: {e}")

    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _set_test_environment() -> None:
    """
    Ensure tests don't depend on real environment secrets.

    Note: `app.config` loads `.env` on import, but having this fixture makes it explicit
    that the defaults are acceptable for most tests (unit-only tests don't need DB).
    """

    # Touch settings to make sure env-based configuration is loaded.
    _ = settings.database_url


pytest_plugins = ("test_discovery_admin_api",)

from search_api_fixtures import embedder, search_client, search_scene  # noqa: E402,F401
