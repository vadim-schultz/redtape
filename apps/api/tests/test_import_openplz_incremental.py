"""End-to-end behaviour of the OpenPLZ import against a fake OpenPLZ client.

The monthly import must write only what changed: a repeat run over identical
input performs no INSERT/UPDATE statements, and a changed row costs one write.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import pytest
from app.models.jurisdiction import Jurisdiction
from app.models.locality import Locality
from scripts import import_openplz_locations as importer
from sqlalchemy import event, func, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

Payload = dict[str, Any]

STATES = [{"key": "14", "name": "Sachsen"}, {"key": "09", "name": "Bayern"}]
DISTRICTS = {
    "14": [
        {"key": "14612", "name": "Dresden", "type": "Kreisfreie Stadt"},
        {"key": "14521", "name": "Erzgebirgskreis", "type": "Landkreis"},
    ],
    "09": [{"key": "09162", "name": "Muenchen", "type": "Kreisfreie Stadt"}],
}
MUNICIPALITIES = {
    "14612": [{"key": "14612000", "name": "Dresden", "type": "Kreisfreie Stadt", "postalCode": "01067"}],
    "14521": [
        {"key": "14521010", "name": "Annaberg-Buchholz", "type": "Stadt", "postalCode": "09456"},
        {"key": "14521020", "name": "Aue", "type": "Stadt", "postalCode": "08280"},
    ],
    "09162": [{"key": "09162000", "name": "Muenchen", "type": "Kreisfreie Stadt", "postalCode": "80331"}],
}
LOCALITIES = {
    "14612": [
        {"name": "Dresden", "postalCode": "01067", "municipality": {"key": "14612000", "name": "Dresden"}},
        {"name": "Loschwitz", "postalCode": "01326", "municipality": {"key": "14612000", "name": "Dresden"}},
    ],
    "14521": [
        {"name": "Annaberg", "postalCode": "09456", "municipality": {"key": "14521010", "name": "Annaberg"}},
        {"name": "Aue", "postalCode": "08280", "municipality": {"key": "14521020", "name": "Aue"}},
    ],
    "09162": [
        {"name": "Altstadt", "postalCode": "80331", "municipality": {"key": "09162000", "name": "Muenchen"}},
    ],
}


def _dataset() -> Payload:
    return copy.deepcopy(
        {"states": STATES, "districts": DISTRICTS, "municipalities": MUNICIPALITIES, "localities": LOCALITIES}
    )


class _FakeClient:
    """Serves the in-memory dataset through the two OpenPLZClient methods the importer uses."""

    def __init__(self, data: Payload) -> None:
        self._data = data

    def get_json(self, endpoint: str, params: dict[str, Any] | None = None) -> list[Payload]:
        assert endpoint == "FederalStates"
        return self._data["states"]

    def iter_paged(self, *, endpoint: str, page_size: int = 50) -> Iterator[Payload]:
        parts = endpoint.split("/")
        if parts[0] == "FederalStates":
            yield from self._data["districts"][parts[1]]
        elif parts[2] == "Municipalities":
            yield from self._data["municipalities"][parts[1]]
        else:
            yield from self._data["localities"][parts[1]]


def _run_import(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    data: Payload,
    *,
    dry_run: bool = False,
    state_codes: set[str] | None = None,
) -> None:
    """Run `import_locations` with the fake client, each run on its own savepoint session."""
    connection = db_session.get_bind()
    monkeypatch.setattr(importer, "OpenPLZClient", lambda **_: _FakeClient(data))
    monkeypatch.setattr(
        importer,
        "SessionLocal",
        lambda: Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint"),
    )
    importer.import_locations("de", dry_run=dry_run, commit_every=2, state_codes=state_codes)


class _WriteLog:
    """Collects the INSERT and UPDATE statements sent to the database."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def _record(self, conn: Connection, cursor: Any, statement: str, *args: Any) -> None:
        self.statements.append(statement.lstrip().split(None, 1)[0].upper())

    def count(self, verb: str) -> int:
        return self.statements.count(verb)

    @property
    def writes(self) -> int:
        return self.count("INSERT") + self.count("UPDATE")


@contextmanager
def _write_log(db_session: Session) -> Iterator[_WriteLog]:
    connection = db_session.get_bind()
    log = _WriteLog()
    event.listen(connection, "before_cursor_execute", log._record)
    try:
        yield log
    finally:
        event.remove(connection, "before_cursor_execute", log._record)


def _counts(db_session: Session) -> tuple[int, int]:
    juris = db_session.execute(select(func.count()).select_from(Jurisdiction)).scalar_one()
    localities = db_session.execute(select(func.count()).select_from(Locality)).scalar_one()
    return juris, localities


def _stamp(db_session: Session, code: str) -> datetime:
    return db_session.execute(select(Jurisdiction.last_updated).where(Jurisdiction.code == code)).scalar_one()


def _name(db_session: Session, code: str) -> str:
    return db_session.execute(select(Jurisdiction.name_i18n["de"].astext).where(Jurisdiction.code == code)).scalar_one()


def _parent_code(db_session: Session, code: str) -> str | None:
    parent = Jurisdiction.__table__.alias("parent")
    child = Jurisdiction.__table__.alias("child")
    stmt = select(parent.c.code).join(child, child.c.geographic_parent_id == parent.c.id).where(child.c.code == code)
    return db_session.execute(stmt).scalar_one_or_none()


def _first_import(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> Payload:
    data = _dataset()
    _run_import(monkeypatch, db_session, data)
    return data


# Loop A -- a repeat run over identical input is a no-op.


def test_first_import_writes_rows(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    with _write_log(db_session) as log:
        _first_import(monkeypatch, db_session)

    assert log.count("INSERT") > 0
    assert _counts(db_session) == (1 + 2 + 3 + 4, 5)


def test_second_import_over_identical_input_performs_no_writes(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    data = _first_import(monkeypatch, db_session)

    with _write_log(db_session) as log:
        _run_import(monkeypatch, db_session, data)

    assert log.writes == 0


def test_second_import_over_identical_input_leaves_row_counts_unchanged(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    data = _first_import(monkeypatch, db_session)
    before = _counts(db_session)

    _run_import(monkeypatch, db_session, data)

    assert _counts(db_session) == before


# Loop B -- a change is applied once, to exactly the rows it touches.


def test_renamed_municipality_updates_exactly_that_row(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    data = _first_import(monkeypatch, db_session)
    sibling_stamp = _stamp(db_session, "14521020")
    data["municipalities"]["14521"][0]["name"] = "Annaberg"

    with _write_log(db_session) as log:
        _run_import(monkeypatch, db_session, data)

    assert (log.count("UPDATE"), log.count("INSERT")) == (1, 0)
    assert _name(db_session, "14521010") == "Annaberg"
    assert _stamp(db_session, "14521020") == sibling_stamp


def test_unchanged_run_keeps_last_updated_of_every_row(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    data = _first_import(monkeypatch, db_session)
    stamps = {code: _stamp(db_session, code) for code in ("14", "14612", "14612000")}

    _run_import(monkeypatch, db_session, data)

    assert {code: _stamp(db_session, code) for code in stamps} == stamps


def test_reparented_district_moves_to_the_new_parent(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    data = _first_import(monkeypatch, db_session)
    bavaria = db_session.execute(select(Jurisdiction.id).where(Jurisdiction.code == "09")).scalar_one()
    db_session.execute(update(Jurisdiction).where(Jurisdiction.code == "14521").values(geographic_parent_id=bavaria))
    assert _parent_code(db_session, "14521") == "09"

    with _write_log(db_session) as log:
        _run_import(monkeypatch, db_session, data)

    assert _parent_code(db_session, "14521") == "14"
    assert (log.count("UPDATE"), log.count("INSERT")) == (1, 0)


def test_reparented_district_keeps_the_row_instead_of_duplicating_it(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    data = _first_import(monkeypatch, db_session)
    bavaria = db_session.execute(select(Jurisdiction.id).where(Jurisdiction.code == "09")).scalar_one()
    db_session.execute(update(Jurisdiction).where(Jurisdiction.code == "14521").values(geographic_parent_id=bavaria))
    before = _counts(db_session)

    _run_import(monkeypatch, db_session, data)

    assert _counts(db_session) == before


def test_new_locality_is_inserted_and_unchanged_siblings_are_untouched(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    data = _first_import(monkeypatch, db_session)
    sibling_stamp = db_session.execute(select(Locality.last_updated).where(Locality.name == "Aue")).scalar_one()
    data["localities"]["14521"].append(
        {"name": "Schlettau", "postalCode": "09487", "municipality": {"key": "14521010", "name": "Annaberg"}}
    )

    with _write_log(db_session) as log:
        _run_import(monkeypatch, db_session, data)

    assert (log.count("INSERT"), log.count("UPDATE")) == (1, 0)
    assert _counts(db_session)[1] == 6
    assert db_session.execute(select(Locality.last_updated).where(Locality.name == "Aue")).scalar_one() == sibling_stamp


def test_locality_moved_to_another_municipality_is_updated_once(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    data = _first_import(monkeypatch, db_session)
    muni_id = db_session.execute(select(Jurisdiction.id).where(Jurisdiction.code == "14521020")).scalar_one()
    db_session.execute(update(Locality).where(Locality.name == "Annaberg").values(municipality_id=muni_id))

    with _write_log(db_session) as log:
        _run_import(monkeypatch, db_session, data)

    moved = db_session.execute(
        select(Jurisdiction.code)
        .join(Locality, Locality.municipality_id == Jurisdiction.id)
        .where(Locality.name == "Annaberg")
    ).scalar_one()
    assert moved == "14521010"
    assert (log.count("UPDATE"), log.count("INSERT")) == (1, 0)


# Loop C -- flags keep their meaning.


def test_states_flag_imports_only_the_selected_state(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _run_import(monkeypatch, db_session, _dataset(), state_codes={"14"})

    codes = set(db_session.execute(select(Jurisdiction.code)).scalars())
    assert {"DE", "14", "14612000"} <= codes
    assert not codes & {"09", "09162", "09162000"}


def test_states_flag_leaves_unselected_states_out_of_the_localities(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _run_import(monkeypatch, db_session, _dataset(), state_codes={"14"})

    assert db_session.execute(select(Locality.id).where(Locality.name == "Altstadt")).first() is None


def test_dry_run_commits_nothing(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    before = _counts(db_session)

    _run_import(monkeypatch, db_session, _dataset(), dry_run=True)

    assert _counts(db_session) == before


def test_dry_run_after_a_real_import_changes_nothing(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    data = _first_import(monkeypatch, db_session)
    data["municipalities"]["14521"][0]["name"] = "Renamed"

    _run_import(monkeypatch, db_session, data, dry_run=True)

    assert _name(db_session, "14521010") == "Annaberg-Buchholz"
