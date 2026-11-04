from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import scripts.issue_api_key as issue_api_key_script
import sqlalchemy as sa
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from scripts.issue_api_key import main
from sqlalchemy.orm import Session


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for `SessionLocal()`: hands the script the fixture's session without closing it."""

    yield session


@pytest.fixture(autouse=True)
def _use_test_session(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issue_api_key_script, "SessionLocal", lambda: _keep_open(db_session))


def test_script_prints_the_key_once_and_exits_0(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["issue_api_key.py", "--name", "crawler-prod"])

    main()

    out = capsys.readouterr().out
    assert out.count("rt_") == 1

    row = db_session.execute(sa.text("SELECT key_hash FROM api_key")).mappings().one()
    assert row["key_hash"] not in out


def test_script_revoke_marks_the_key_revoked(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    key = ApiKeyService(ApiKeyRepository(db_session)).issue("crawler-prod")
    prefix = key.removeprefix("rt_")[:8]
    # `--revoke=PREFIX` keeps the prefix as the option's value: a token_urlsafe prefix may start with `-`,
    # which argparse would otherwise read as a flag.
    monkeypatch.setattr("sys.argv", ["issue_api_key.py", f"--revoke={prefix}"])

    main()

    revoked_at = db_session.execute(
        sa.text("SELECT revoked_at FROM api_key WHERE key_prefix = :prefix"), {"prefix": prefix}
    ).scalar_one()
    assert revoked_at is not None


def test_script_revoke_of_an_unknown_prefix_exits_nonzero(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["issue_api_key.py", "--revoke", "ghosthost"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0
