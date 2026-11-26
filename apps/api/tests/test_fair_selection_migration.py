"""Fair-selection migration on a database that already has task rows: the backfill and the round trip."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from test_check_migrations_script import _fresh_database
from test_search_migration import _alembic, _scalars

PRE_FAIR_SELECTION = "20261119_fetch_body_sha256"
JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111111")
CANDIDATE = uuid.UUID("22222222-2222-2222-2222-222222222222")
CATALOGUE_SERVICE = uuid.UUID("33333333-3333-3333-3333-333333333333")
SEED_STATEMENTS = (
    "insert into jurisdiction (id, kind) values (:j, 'COUNTRY')",
    "insert into discovery_document_candidate (id, jurisdiction_id, key) values (:c, :j, 'k1')",
    "insert into catalogue_service (id, source, external_id, jurisdiction_id, pipeline_stage) "
    "values (:s, 'manual', 'ext1', :j, 'T0')",
    "insert into translation_task (id, candidate_id, locale, source_hash) values (gen_random_uuid(), :c, 'de', 'h1')",
    # A second task on the same candidate: the backfill must still write one state row for it.
    "insert into translation_task (id, candidate_id, locale, source_hash) values (gen_random_uuid(), :c, 'en', 'h2')",
    "insert into embedding_task (id, candidate_id, model, locale, text_hash) "
    "values (gen_random_uuid(), :c, 'm', 'de', 'h3')",
    "insert into snapshot_translation_task (id, catalogue_service_id, locale, source_hash) "
    "values (gen_random_uuid(), :s, 'de', 'h4')",
    "insert into discovery_task (id, catalogue_service_id, kind, target_url) "
    "values (gen_random_uuid(), :s, 'fetch_url', 'https://example.test/a')",
)
EXPECTED_STATE = [
    ("discovery", str(CATALOGUE_SERVICE), 1, 0),
    ("embedding", str(CANDIDATE), 1, 0),
    ("snapshot_translation", str(CATALOGUE_SERVICE), 1, 0),
    ("translation", str(CANDIDATE), 1, 0),
]


@pytest.fixture
def seeded_before_fair_selection() -> Iterator[tuple[str, Engine]]:
    """Yield a database at the pre-fair-selection revision that already holds task rows."""
    with _fresh_database() as url:
        _alembic(url, "upgrade", PRE_FAIR_SELECTION)
        engine = create_engine(url)
        try:
            _seed(engine)
            yield url, engine
        finally:
            engine.dispose()


def _seed(engine: Engine) -> None:
    """Insert one jurisdiction, candidate, catalogue service and a task in each pipeline."""
    params = {"j": JURISDICTION, "c": CANDIDATE, "s": CATALOGUE_SERVICE}
    with engine.begin() as connection:
        for statement in SEED_STATEMENTS:
            connection.execute(text(statement), params)


def _state_rows(engine: Engine) -> list[tuple[str, str, int, int]]:
    """Return every fair_selection_state row as (pipeline, entity_id, phase, coverage_bitmap)."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select pipeline, entity_id::text, phase, coverage_bitmap "
                "from fair_selection_state order by pipeline, entity_id"
            )
        ).all()
    return [(pipeline, entity, phase, bitmap) for pipeline, entity, phase, bitmap in rows]


def test_upgrade_backfills_one_phase_one_state_row_per_entity(seeded_before_fair_selection: tuple[str, Engine]) -> None:
    """Happy path: the upgrade reaches head, writes one state row per (pipeline, entity) and leaves task phases at 1."""
    url, engine = seeded_before_fair_selection

    _alembic(url, "upgrade", "head")

    assert _state_rows(engine) == sorted(EXPECTED_STATE, key=lambda row: (row[0], row[1]))
    assert _scalars(engine, "select phase::text from translation_task order by phase") == ["1", "1"]


def test_downgrade_drops_state_and_phase_keeps_task_rows_and_upgrade_rebuilds_it(
    seeded_before_fair_selection: tuple[str, Engine],
) -> None:
    """Negative path: downgrade leaves no state table or phase column and no task row is lost; re-upgrade rebuilds the same state."""
    url, engine = seeded_before_fair_selection
    _alembic(url, "upgrade", "head")
    before = _state_rows(engine)

    _alembic(url, "downgrade", PRE_FAIR_SELECTION)

    assert _scalars(engine, "select coalesce(to_regclass('fair_selection_state')::text, 'absent')") == ["absent"]
    assert _scalars(engine, "select count(*)::text from translation_task") == ["2"]
    assert _scalars(engine, "select column_name from information_schema.columns where table_name = 'translation_task' and column_name = 'phase'") == []

    _alembic(url, "upgrade", "head")

    assert _state_rows(engine) == before
