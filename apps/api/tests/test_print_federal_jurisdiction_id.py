"""Tests for ``scripts.print_federal_jurisdiction_id``."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import scripts.print_federal_jurisdiction_id as print_federal_script
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from scripts.print_federal_jurisdiction_id import main
from scripts.seed_documents import ID_DE
from sqlalchemy.orm import Session


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for ``SessionLocal()`` without closing the fixture session."""

    yield session


@pytest.fixture(autouse=True)
def _use_test_session(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(print_federal_script, "SessionLocal", lambda: _keep_open(db_session))


def test_print_federal_jurisdiction_id_prints_uuid_for_seeded_de(
    db_session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    """Script prints the id of the seeded Germany country row."""
    db_session.add(
        Jurisdiction(
            id=ID_DE,
            kind=JurisdictionKind.COUNTRY,
            geographic_parent_id=None,
            code="DE",
            administrative_roles=["COUNTRY"],
            name_i18n={"de": "Deutschland", "en": "Germany"},
        )
    )
    db_session.flush()

    main()

    out = capsys.readouterr().out.strip()
    assert uuid.UUID(out) == ID_DE


def test_print_federal_jurisdiction_id_exits_nonzero_when_de_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Script fails when no COUNTRY DE jurisdiction exists."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code != 0
