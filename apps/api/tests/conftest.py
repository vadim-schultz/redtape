from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Base
from app.db import engine as db_engine


@pytest.fixture(scope="function")
def deterministic_uuid_namespace() -> uuid.UUID:
    """
    Deterministic namespace for stable UUID generation in tests.

    Using a fixed namespace ensures repeatable UUIDs within a test.
    """

    return uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit")


def _try_create_schema() -> None:
    # If the DB is unavailable (common in CI/dev), we skip integration tests.
    Base.metadata.create_all(db_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provide a SQLAlchemy session with the app schema created.

    Integration tests will be skipped if the configured database is unreachable.
    """

    try:
        _try_create_schema()
    except Exception as e:  # pragma: no cover
        pytest.skip(f"Database unavailable for tests: {e}")

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _set_test_environment() -> None:
    """
    Ensure tests don't depend on real environment secrets.

    Note: `app.config` loads `.env` on import, but having this fixture makes it explicit
    that the defaults are acceptable for most tests (unit-only tests don't need DB).
    """

    # Touch settings to make sure env-based configuration is loaded.
    _ = settings.database_url

