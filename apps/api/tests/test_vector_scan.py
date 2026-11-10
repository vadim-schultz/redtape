"""Session settings of the vector leg: iterative HNSW scan, exact scan, and the fallback on an older pgvector."""

from __future__ import annotations

import pytest
from app.features.search import vector_scan
from app.features.search.vector import _nearest
from sqlalchemy import text
from sqlalchemy.orm import Session

from search_query_world import params, query_vector


def setting(session: Session, name: str) -> str:
    return str(session.execute(text(f"show {name}")).scalar_one())


def test_the_iterative_scan_is_switched_on_for_the_transaction(db_session: Session) -> None:
    vector_scan.apply_vector_scan(db_session, index_enabled=True)

    assert setting(db_session, "hnsw.iterative_scan") == "relaxed_order"
    assert setting(db_session, "enable_indexscan") == "on"


def test_turning_the_index_off_forces_an_exact_scan(db_session: Session) -> None:
    vector_scan.apply_vector_scan(db_session, index_enabled=False)

    assert setting(db_session, "enable_indexscan") == "off"


def test_a_server_without_the_iterative_scan_falls_back_to_an_exact_scan_and_stays_usable(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vector_scan, "MIN_ITERATIVE_VERSION", (99, 0))

    vector_scan.apply_vector_scan(db_session, index_enabled=True)

    assert setting(db_session, "enable_indexscan") == "off"
    assert db_session.execute(text("select 1")).scalar_one() == 1


def test_the_cut_off_stays_out_of_the_ordered_hnsw_query() -> None:
    nearest = _nearest(query_vector(), "de", params(), None)

    assert "<=" not in str(nearest.element.whereclause)
