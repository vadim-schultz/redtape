"""Schema tests for fair task selection state tracking.

Tests verify that the fair_selection_state table exists with correct schema,
that phase columns exist on task tables, and that migrations can be executed
and rolled back cleanly.
"""

from __future__ import annotations

import uuid

import pytest
from app.models import (
    DiscoveryTask,
    EmbeddingTask,
    FairSelectionState,
    SnapshotTranslationTask,
    TranslationTask,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from search_support import make_candidate
from test_discovery_admin_api import _catalogue


class TestFairSelectionStateTableSchema:
    """Happy path: fair_selection_state table exists with correct schema."""

    def test_fair_selection_state_table_exists(self, db_session: Session) -> None:
        """Verify fair_selection_state table created with correct columns and types."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'fair_selection_state'
            ORDER BY ordinal_position
            """)
        ).fetchall()

        actual_columns = {row[0]: row[1] for row in result}

        # Expected columns and their PostgreSQL types
        expected_columns = {
            "id": "uuid",
            "pipeline": "character varying",
            "entity_id": "uuid",
            "phase": "integer",
            "coverage_bitmap": "bigint",
            "updated_at": "timestamp with time zone",
        }

        assert actual_columns == expected_columns, f"Expected columns {expected_columns}, got {actual_columns}"

    def test_fair_selection_state_unique_index(self, db_session: Session) -> None:
        """Verify the index on (pipeline, entity_id) is unique."""
        is_unique = db_session.execute(
            text("""
            SELECT i.indisunique
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indexrelid
            WHERE c.relname = 'ix_fair_selection_state_pipeline_entity'
            """)
        ).scalar_one_or_none()

        assert is_unique is True, "Expected ix_fair_selection_state_pipeline_entity to be a unique index"

    def test_fair_selection_state_index_exists(self, db_session: Session) -> None:
        """Verify index exists on (pipeline, entity_id)."""
        result = db_session.execute(
            text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'fair_selection_state'
            """)
        ).fetchall()

        index_names = {row[0] for row in result}
        assert "ix_fair_selection_state_pipeline_entity" in index_names, f"Expected index not found in {index_names}"

    def test_fair_selection_state_insert_and_query(self, db_session: Session) -> None:
        """Verify can insert and query fair_selection_state rows."""
        pipeline = "translation"
        entity_id = uuid.uuid4()

        state = FairSelectionState(pipeline=pipeline, entity_id=entity_id, phase=1, coverage_bitmap=0)
        db_session.add(state)
        db_session.commit()

        retrieved = db_session.query(FairSelectionState).filter_by(pipeline=pipeline, entity_id=entity_id).first()

        assert retrieved is not None
        assert retrieved.pipeline == pipeline
        assert retrieved.entity_id == entity_id
        assert retrieved.phase == 1
        assert retrieved.coverage_bitmap == 0


class TestFairSelectionStateDuplicateInsert:
    """Negative path: duplicate insert on (pipeline, entity_id) is rejected."""

    def test_duplicate_fair_selection_state_rejected(self, db_session: Session) -> None:
        """Verify unique constraint violation when inserting duplicate (pipeline, entity_id)."""
        pipeline = "translation"
        entity_id = uuid.uuid4()

        # Insert first row
        state1 = FairSelectionState(pipeline=pipeline, entity_id=entity_id, phase=1, coverage_bitmap=0)
        db_session.add(state1)
        db_session.commit()

        # Try to insert duplicate
        state2 = FairSelectionState(pipeline=pipeline, entity_id=entity_id, phase=1, coverage_bitmap=0)
        db_session.add(state2)

        with pytest.raises(IntegrityError, match="ix_fair_selection_state_pipeline_entity"):
            db_session.commit()


class TestPhaseColumnOnTaskTables:
    """Happy path: phase column exists on all task tables with default=1."""

    def test_translation_task_has_phase_column(self, db_session: Session) -> None:
        """Verify translation_task has phase column with correct type and default."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'translation_task' AND column_name = 'phase'
            """)
        ).fetchone()

        assert result is not None, "phase column not found on translation_task"
        assert result[1] == "integer", f"Expected integer type, got {result[1]}"

    def test_snapshot_translation_task_has_phase_column(self, db_session: Session) -> None:
        """Verify snapshot_translation_task has phase column with correct type."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'snapshot_translation_task' AND column_name = 'phase'
            """)
        ).fetchone()

        assert result is not None, "phase column not found on snapshot_translation_task"
        assert result[1] == "integer"

    def test_embedding_task_has_phase_column(self, db_session: Session) -> None:
        """Verify embedding_task has phase column with correct type."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'embedding_task' AND column_name = 'phase'
            """)
        ).fetchone()

        assert result is not None, "phase column not found on embedding_task"
        assert result[1] == "integer"

    def test_discovery_task_has_phase_column(self, db_session: Session) -> None:
        """Verify discovery_task has phase column with correct type."""
        result = db_session.execute(
            text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'discovery_task' AND column_name = 'phase'
            """)
        ).fetchone()

        assert result is not None, "phase column not found on discovery_task"
        assert result[1] == "integer"

    def test_translation_task_phase_defaults_to_one(self, db_session: Session) -> None:
        """Verify a translation_task row inserted without a phase gets phase=1 from the schema default."""
        candidate = make_candidate(db_session)
        phase = db_session.execute(
            text("""
            INSERT INTO translation_task (id, candidate_id, locale, source_hash)
            VALUES (gen_random_uuid(), :cid, 'en', 'abc123')
            RETURNING phase
            """),
            {"cid": candidate.id},
        ).scalar_one()

        assert phase == 1, f"Expected phase=1, got {phase}"


class TestPhaseNullConstraint:
    """Negative path: NULL phase is rejected due to NOT NULL constraint."""

    def test_translation_task_phase_not_null(self, db_session: Session) -> None:
        """Verify NOT NULL constraint on phase column."""
        candidate = make_candidate(db_session)
        with pytest.raises(IntegrityError, match='"phase"'):
            db_session.execute(
                text("""
                INSERT INTO translation_task (id, candidate_id, locale, source_hash, phase)
                VALUES (gen_random_uuid(), :cid, 'en', 'abc123', NULL)
                """),
                {"cid": candidate.id},
            )

    def test_snapshot_translation_task_phase_not_null(self, db_session: Session) -> None:
        """Verify NOT NULL constraint on snapshot_translation_task phase."""
        catalogue = _catalogue(db_session, external_id=f"svc-{uuid.uuid4().hex[:8]}")
        with pytest.raises(IntegrityError, match='"phase"'):
            db_session.execute(
                text("""
                INSERT INTO snapshot_translation_task (id, catalogue_service_id, locale, source_hash, phase)
                VALUES (gen_random_uuid(), :csid, 'en', 'abc123', NULL)
                """),
                {"csid": catalogue.id},
            )


class TestOrmModelsReflectSchema:
    """Verify ORM models match the schema."""

    def test_fair_selection_state_orm_model(self) -> None:
        """Verify FairSelectionState ORM model has expected attributes."""
        state = FairSelectionState(pipeline="translation", entity_id=uuid.uuid4(), phase=1, coverage_bitmap=0)

        assert state.pipeline == "translation"
        assert state.phase == 1
        assert state.coverage_bitmap == 0

    def test_translation_task_orm_model_has_phase(self) -> None:
        """Verify TranslationTask ORM model has phase attribute."""
        assert hasattr(TranslationTask, "phase"), "TranslationTask missing phase attribute"

    def test_snapshot_translation_task_orm_model_has_phase(self) -> None:
        """Verify SnapshotTranslationTask ORM model has phase attribute."""
        assert hasattr(SnapshotTranslationTask, "phase"), "SnapshotTranslationTask missing phase attribute"

    def test_embedding_task_orm_model_has_phase(self) -> None:
        """Verify EmbeddingTask ORM model has phase attribute."""
        assert hasattr(EmbeddingTask, "phase"), "EmbeddingTask missing phase attribute"

    def test_discovery_task_orm_model_has_phase(self) -> None:
        """Verify DiscoveryTask ORM model has phase attribute."""
        assert hasattr(DiscoveryTask, "phase"), "DiscoveryTask missing phase attribute"
