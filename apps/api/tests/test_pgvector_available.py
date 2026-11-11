"""pgvector and unaccent are installed in the test database and a vector round trips through cosine distance."""

from __future__ import annotations

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, MetaData, Table, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

_SCRATCH = Table("pgvector_probe_scratch", MetaData(), Column("id", Integer, primary_key=True), Column("v", Vector(3)))


def test_extension_is_available_and_a_vector_round_trips(db_session: Session) -> None:
    """pgvector · extension is available and a vector round trips."""
    version = db_session.execute(text("select extversion from pg_extension where extname = 'vector'")).scalar()
    assert version, "the vector extension is not installed in the test database"

    _SCRATCH.create(db_session.connection())
    db_session.execute(_SCRATCH.insert(), [{"id": 1, "v": [1.0, 0.0, 0.0]}, {"id": 2, "v": [0.0, 1.0, 0.0]}])
    nearest = db_session.execute(
        select(_SCRATCH.c.id, _SCRATCH.c.v.cosine_distance([0.9, 0.1, 0.0])).order_by(
            _SCRATCH.c.v.cosine_distance([0.9, 0.1, 0.0])
        )
    ).all()

    assert [row[0] for row in nearest] == [1, 2]
    assert nearest[0][1] < nearest[1][1]


def test_unaccent_is_available(db_session: Session) -> None:
    """pgvector · the unaccent extension answers, so later search text can fold diacritics."""
    assert db_session.execute(select(func.unaccent("Kindergeld Äpfel"))).scalar() == "Kindergeld Apfel"


def test_a_vector_of_the_wrong_dimension_is_rejected(db_session: Session) -> None:
    """pgvector · a vector whose length differs from the column dimension fails instead of truncating."""
    _SCRATCH.create(db_session.connection())

    with pytest.raises(DBAPIError):
        db_session.execute(_SCRATCH.insert(), [{"id": 1, "v": [1.0, 0.0]}])
