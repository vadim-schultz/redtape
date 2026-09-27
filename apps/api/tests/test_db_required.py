from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from app.models import Document, Jurisdiction, JurisdictionKind
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parent.parent
BAD_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:1/redtape"
TARGET_TEST = "tests/test_db_required.py::test_db_session_yields_a_working_session"


def _run_pytest_against_bad_db(require_db: str | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = BAD_DATABASE_URL
    if require_db is None:
        env.pop("REQUIRE_DB", None)
    else:
        env["REQUIRE_DB"] = require_db
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-rs", TARGET_TEST],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_require_db_with_an_unreachable_database_raises_instead_of_skipping() -> None:
    result = _run_pytest_against_bad_db(require_db="1")

    assert result.returncode != 0
    assert "skipped" not in result.stdout.lower()


def test_require_db_unset_with_an_unreachable_database_skips_with_a_reason() -> None:
    result = _run_pytest_against_bad_db(require_db=None)

    assert result.returncode == 0
    assert "Database unavailable" in result.stdout


def test_db_session_yields_a_working_session(db_session) -> None:
    session = db_session

    assert session.execute(select(1)).scalar_one() == 1
    assert session.bind.dialect.name == "postgresql"


def test_jsonb_column_round_trips_through_db_session(db_session) -> None:
    session = db_session
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.unit.db_required")

    jurisdiction = Jurisdiction(id=uuid.uuid5(ns, "jurisdiction"), kind=JurisdictionKind.COUNTRY, code="ci-jsonb")
    document = Document(
        id=uuid.uuid5(ns, "document"),
        jurisdiction_id=jurisdiction.id,
        slug="ci-jsonb-doc",
        title_i18n={"en": "Passport", "de": "Reisepass"},
    )
    session.add_all([jurisdiction, document])
    session.commit()

    reloaded = session.execute(select(Document).where(Document.id == document.id)).scalar_one()
    assert reloaded.title_i18n == {"en": "Passport", "de": "Reisepass"}


def test_no_leak_a(db_session) -> None:
    db_session.add(Jurisdiction(kind=JurisdictionKind.COUNTRY, code="ci-no-leak"))
    db_session.commit()


def test_no_leak_b(db_session) -> None:
    db_session.add(Jurisdiction(kind=JurisdictionKind.COUNTRY, code="ci-no-leak"))
    db_session.commit()
