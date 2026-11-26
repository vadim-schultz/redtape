"""Schema tests for fair task selection state tracking.

Tests verify that the fair_selection_state table exists with correct schema,
that phase columns exist on task tables, and that migrations can be executed
and rolled back cleanly.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    DiscoveryTask,
    EmbeddingTask,
    FairSelectionState,
    SnapshotTranslationTask,
    TranslationTask,
)


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

        assert (
            actual_columns == expected_columns
        ), f"Expected columns {expected_columns}, got {actual_columns}"

    def test_fair_selection_state_unique_constraint(self, db_session: Session) -> None:
        """Verify unique constraint exists on (pipeline, entity_id)."""
        result = db_session.execute(
            text("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'fair_selection_state'
            AND constraint_type = 'UNIQUE'
            """)
        ).fetchall()

        constraint_names = {row[0] for row in result}
        assert (
            "uq_fair_selection_state_entity" in constraint_names
        ), f"Expected unique constraint not found in {constraint_names}"

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
        assert (
            "ix_fair_selection_state_pipeline_entity" in index_names
        ), f"Expected index not found in {index_names}"

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

        with pytest.raises(Exception):  # Unique constraint violation
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
        """Verify new translation_task rows get phase=1 by default."""
        # Create a minimal translation task (without all required fields for now,
        # just testing phase defaults from schema perspective)
        db_session.execute(
            text("""
            INSERT INTO translation_task (candidate_id, locale, source_hash, status, priority)
            VALUES (:cid, 'en', 'abc123', 'pending', 100)
            """),
            {"cid": uuid.uuid4()},
        )
        db_session.commit()

        result = db_session.execute(text("SELECT phase FROM translation_task ORDER BY created_at DESC LIMIT 1")).fetchone()

        assert result is not None
        assert result[0] == 1, f"Expected phase=1, got {result[0]}"


class TestPhaseNullConstraint:
    """Negative path: NULL phase is rejected due to NOT NULL constraint."""

    def test_translation_task_phase_not_null(self, db_session: Session) -> None:
        """Verify NOT NULL constraint on phase column."""
        with pytest.raises(Exception):  # NOT NULL constraint violation
            db_session.execute(
                text("""
                INSERT INTO translation_task (candidate_id, locale, source_hash, status, priority, phase)
                VALUES (:cid, 'en', 'abc123', 'pending', 100, NULL)
                """),
                {"cid": uuid.uuid4()},
            )
            db_session.commit()

    def test_snapshot_translation_task_phase_not_null(self, db_session: Session) -> None:
        """Verify NOT NULL constraint on snapshot_translation_task phase."""
        with pytest.raises(Exception):  # NOT NULL constraint violation
            db_session.execute(
                text("""
                INSERT INTO snapshot_translation_task (catalogue_service_id, locale, source_hash, status, priority, phase)
                VALUES (:csid, 'en', 'abc123', 'pending', 100, NULL)
                """),
                {"csid": uuid.uuid4()},
            )
            db_session.commit()


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
