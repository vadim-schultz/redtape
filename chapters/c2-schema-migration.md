---
name: Chapter C2 - Create fair_selection_state table & migration
overview: "Establish the fair_selection_state table, add phase columns to task tables, and backfill initial state for all pipelines."
id: C2
depends_on: []
touches:
  - apps/api/alembic/versions/
  - apps/api/app/models/translation.py
  - apps/api/app/models/snapshot_translation.py
  - apps/api/app/models/search.py
  - apps/api/app/models/discovery/discovery_task.py
  - tests/
execution: chapter-implementer
isProject: false
---

# C2 - Create fair_selection_state table & migration

**Depends on:** (none) · **Architecture:** `/mnt/projects/redtape/plans/fair-task-selection/architecture.md` · **Rollout:** `/mnt/projects/redtape/plans/fair-task-selection/rollout.md`

## Goal

Create the `fair_selection_state` table to track document coverage across five pipelines (translation, snapshot translation, embedding, discovery, search), add `phase` columns to task tables, and backfill initial state. This schema change enables fair task selection logic in C3–C10.

## Read first

- **Architecture**: Introduction and pipeline mapping.
- **Rollout**: State machine and phase definitions.

## Coordination scope

**Add:**

- `apps/api/alembic/versions/20261124_fair_selection_state.py` — migration file creating `fair_selection_state` table, adding `phase` columns, and backfilling state

**Edit:**

- `apps/api/app/models/translation.py` — add `phase` column to `TranslationTask`
- `apps/api/app/models/snapshot_translation.py` — add `phase` column to `SnapshotTranslationTask`
- `apps/api/app/models/search.py` — add `phase` column to `EmbeddingTask`
- `apps/api/app/models/discovery/discovery_task.py` — add `phase` column to `DiscoveryTask`
- `tests/features/fair_selection/test_schema.py` — new schema test suite

**Do not edit:**

- Other chapters' files or owned areas (none yet; C2 is first)

## Work items

### Slice 1: fair_selection_state table & index

**Red: Two test descriptions**

1. **Happy path** — `test_fair_selection_state_table_exists_with_correct_schema`
   - Verify table `fair_selection_state` exists in database after migration
   - Verify columns exist: `id` (UUID, primary key), `pipeline` (TEXT, non-null), `entity_id` (UUID, non-null), `phase` (INTEGER, non-null, default=1), `coverage_bitmap` (BIGINT, non-null, default=0), `updated_at` (TIMESTAMP, non-null, server default=now())
   - Verify unique constraint on `(pipeline, entity_id)` exists
   - Verify index on `(pipeline, entity_id)` exists

2. **Negative path** — `test_fair_selection_state_duplicate_entity_rejected`
   - Insert a valid row: `(id=uuid(), pipeline='translation', entity_id=uuid(), phase=1, coverage_bitmap=0)`
   - Attempt insert duplicate with same `(pipeline, entity_id)` but different `id`
   - Assert raises `IntegrityError` with unique constraint violation (not silent failure or partial success)

**Green: Minimal Alembic migration**

Create migration file `apps/api/alembic/versions/20261124_fair_selection_state.py`:

```python
"""Create fair_selection_state table for phase tracking across pipelines.

Revision ID: 20261124_fair_selection_state
Revises: <LATEST_MIGRATION>
Create Date: 2026-11-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261124_fair_selection_state"
down_revision: str | None = "<LATEST_MIGRATION>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fair_selection_state",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("coverage_bitmap", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline", "entity_id", name="uq_fair_selection_state_entity"),
    )
    op.create_index(
        "ix_fair_selection_state_pipeline_entity",
        "fair_selection_state",
        ["pipeline", "entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_fair_selection_state_pipeline_entity", table_name="fair_selection_state")
    op.drop_table("fair_selection_state")
```

**Refactor: Index strategy audit**

- ✅ Index `(pipeline, entity_id)` covers lookups by pipeline and entity; no partial index needed yet (all phases are queried during backfill and fair selection).
- ✅ Unique constraint on `(pipeline, entity_id)` prevents duplicate state rows; `id` is natural key (uuid).
- ✅ No redundant indices; combined index sufficient for access patterns in C3–C8.

---

### Slice 2: Add phase column to task tables

**Red: Two test descriptions**

1. **Happy path** — `test_phase_column_exists_on_all_task_tables`
   - Query information schema: verify `phase` column exists on `translation_task`, `snapshot_translation_task`, `embedding_task`, `discovery_task`
   - Insert new row on each table without specifying `phase`
   - Verify inserted row retrieves `phase=1` (default applied)
   - Assert default value is 1 (server default + ORM default align)

2. **Negative path** — `test_phase_column_not_null_enforced`
   - Attempt insert with explicit `phase=NULL` on `translation_task` (representative)
   - Assert raises `IntegrityError` with NOT NULL constraint violation
   - Verify row not inserted (no partial commit)

**Green: Minimal Alembic migration (continuation of Slice 1 migration)**

Extend `upgrade()` and `downgrade()` in `20261124_fair_selection_state.py`:

```python
def upgrade() -> None:
    # ... fair_selection_state table creation (from Slice 1) ...

    # Add phase column to task tables
    for table_name in ["translation_task", "snapshot_translation_task", "embedding_task", "discovery_task"]:
        op.add_column(
            table_name,
            sa.Column("phase", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )


def downgrade() -> None:
    # ... fair_selection_state teardown (from Slice 1) ...

    for table_name in ["translation_task", "snapshot_translation_task", "embedding_task", "discovery_task"]:
        op.drop_column(table_name, "phase")
```

**Refactor: Column placement and naming**

- ✅ Combine phase additions into single migration file (Slice 1); reduces round-trips and keeps schema change atomic.
- ✅ Column name `phase` is consistent with plan and matches `fair_selection_state.phase` for joins.
- ✅ Server default `1` matches ORM default; no ambiguity at database level.
- ✅ One logical operation (add phase tracking); no extraction needed.

---

### Slice 3: SQLAlchemy ORM model updates

**Red: Two test descriptions**

1. **Happy path** — `test_orm_models_reflect_phase_column`
   - Create in-memory instance: `task = DiscoveryTask(..., phase=1)` (all four task classes)
   - Verify attribute `task.phase == 1`
   - Persist to test database and retrieve
   - Verify persisted row reads back `phase=1`
   - Assert mapping is bidirectional (Python object ↔ database column)

2. **Negative path** — `test_orm_validation_rejects_invalid_phase`
   - Attempt assign invalid phase: `task.phase = -1` or `task.phase = 999` or `task.phase = None`
   - Assert Pydantic validator raises `ValidationError` with message naming valid phases, OR
   - Assert constraint violation on flush (defer enforcement to database if ORM validator not implemented in this slice)
   - Verify task not persisted (no partial commit)

**Green: Minimal ORM model updates**

Update each task model to include phase column mapping:

**`apps/api/app/models/translation.py`**

```python
# In class TranslationTask(TimestampMixin, Base):
phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
```

**`apps/api/app/models/snapshot_translation.py`**

```python
# In class SnapshotTranslationTask(TimestampMixin, Base):
phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
```

**`apps/api/app/models/search.py`**

```python
# In class EmbeddingTask(TimestampMixin, Base):
phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
```

**`apps/api/app/models/discovery/discovery_task.py`**

```python
# In class DiscoveryTask(TimestampMixin, Base):
phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
```

Add docstring to each class if not present, update if needed:

```python
"""Leased unit of work, with phase tracking for fair task selection."""
```

**Refactor: ORM audit**

- ✅ Type annotation `Mapped[int]` is precise (not `Any` or `object`); matches database INTEGER.
- ✅ Default and server_default match; ORM layer and database layer agree on initial state.
- ✅ No validation logic added in this slice (defer to C3 if business rules are needed).
- ✅ All four task models are identical in shape; no duplication extraction needed (yet; if validation is added, consider factory in next loop).

---

### Slice 4: Backfill script for existing tasks

**Red: Two test descriptions**

1. **Happy path** — `test_backfill_populates_fair_selection_state`
   - Setup test database with mock data:
     - 10 translation candidates × 5 locales = 50 `translation_task` rows (5 unique candidates)
     - 3 catalogue services × 4 locales = 12 `snapshot_translation_task` rows (3 unique entities)
     - 10 candidates × 2 models × 3 locales = 60 `embedding_task` rows (10 unique candidates)
     - 8 catalogue services = 8 `discovery_task` rows
   - Run backfill
   - Query `fair_selection_state`:
     - `SELECT COUNT(*) FROM fair_selection_state WHERE pipeline='translation'` → 5 (one per candidate)
     - `SELECT COUNT(*) FROM fair_selection_state WHERE pipeline='snapshot_translation'` → 3 (one per catalogue service)
     - `SELECT COUNT(*) FROM fair_selection_state WHERE pipeline='embedding'` → 10 (one per candidate)
     - `SELECT COUNT(*) FROM fair_selection_state WHERE pipeline='discovery'` → 8 (one per catalogue service)
   - Assert all rows have `phase=1`, `coverage_bitmap=0`, `updated_at` set to now (within 1 second)

2. **Negative path** — `test_backfill_idempotent_on_rerun`
   - Run backfill
   - Verify row count matches Slice 4, Negative path setup (5 translation rows, etc.)
   - Run backfill again (same transaction or new session)
   - Query `fair_selection_state` again
   - Assert row count unchanged (no duplicates)
   - Assert all rows still have `phase=1`, `coverage_bitmap=0`

**Green: Minimal backfill SQL in migration**

Extend `upgrade()` in migration file:

```python
def upgrade() -> None:
    # ... table creation and phase column additions ...

    # Backfill fair_selection_state from existing tasks
    # Translation: one row per candidate
    op.execute("""
        INSERT INTO fair_selection_state (pipeline, entity_id, phase, coverage_bitmap)
        SELECT DISTINCT 'translation', candidate_id, 1, 0
        FROM translation_task
        WHERE candidate_id NOT IN (
            SELECT entity_id FROM fair_selection_state WHERE pipeline = 'translation'
        )
        ON CONFLICT (pipeline, entity_id) DO NOTHING;
    """)

    # Snapshot Translation: one row per catalogue_service_id
    op.execute("""
        INSERT INTO fair_selection_state (pipeline, entity_id, phase, coverage_bitmap)
        SELECT DISTINCT 'snapshot_translation', catalogue_service_id, 1, 0
        FROM snapshot_translation_task
        WHERE catalogue_service_id NOT IN (
            SELECT entity_id FROM fair_selection_state WHERE pipeline = 'snapshot_translation'
        )
        ON CONFLICT (pipeline, entity_id) DO NOTHING;
    """)

    # Embedding: one row per candidate
    op.execute("""
        INSERT INTO fair_selection_state (pipeline, entity_id, phase, coverage_bitmap)
        SELECT DISTINCT 'embedding', candidate_id, 1, 0
        FROM embedding_task
        WHERE candidate_id NOT IN (
            SELECT entity_id FROM fair_selection_state WHERE pipeline = 'embedding'
        )
        ON CONFLICT (pipeline, entity_id) DO NOTHING;
    """)

    # Discovery: one row per catalogue_service_id
    op.execute("""
        INSERT INTO fair_selection_state (pipeline, entity_id, phase, coverage_bitmap)
        SELECT DISTINCT 'discovery', catalogue_service_id, 1, 0
        FROM discovery_task
        WHERE catalogue_service_id NOT IN (
            SELECT entity_id FROM fair_selection_state WHERE pipeline = 'discovery'
        )
        ON CONFLICT (pipeline, entity_id) DO NOTHING;
    """)
```

**Refactor: Backfill logic audit**

- ✅ Each backfill statement is idempotent: `ON CONFLICT ... DO NOTHING` prevents duplicate inserts on rerun.
- ✅ Check `NOT IN` guard ensures no duplicate-key error on first run (defensive; combined with ON CONFLICT).
- ✅ Four separate statements (one per pipeline) are clear and maintainable; no extraction needed (each has distinct table and entity_id column name).
- ✅ No business logic embedded; backfill is mechanical data movement (init state to 1 for all).

---

### Slice 5: Schema test suite (happy + negative paths)

**Red: Two test descriptions**

1. **Happy path** — `test_schema_satisfies_fair_selection_requirements`
   - Run all migrations (including C2) on test database
   - Query information schema for table existence and column definitions:
     - Verify `fair_selection_state` has columns: `id`, `pipeline`, `entity_id`, `phase`, `coverage_bitmap`, `updated_at` with correct types
     - Verify `translation_task`, `snapshot_translation_task`, `embedding_task`, `discovery_task` each have `phase` column, type INTEGER, NOT NULL
   - Verify unique constraints: `fair_selection_state` has UQ on `(pipeline, entity_id)`
   - Verify indices: `fair_selection_state` has index on `(pipeline, entity_id)`
   - Assert all constraints and indices are present and correct

2. **Negative path** — `test_migration_rollback_removes_schema_changes`
   - Upgrade to latest migration (including C2)
   - Verify `fair_selection_state` exists and task tables have `phase`
   - Downgrade to previous migration (before C2)
   - Query information schema:
     - Assert `fair_selection_state` table does not exist
     - Assert `phase` column does not exist on task tables
   - Assert downgrades cleanly (no errors, no hanging locks)

**Green: Minimal test file**

Create `tests/features/fair_selection/test_schema.py`:

```python
"""Schema tests for fair_selection_state table and phase tracking.

Happy path: table exists with correct schema, indices, and constraints.
Negative path: migration rollback removes all changes.
"""

from __future__ import annotations

from sqlalchemy import text

import pytest


class TestFairSelectionStateSchema:
    """Test fair_selection_state table schema and constraints."""

    def test_fair_selection_state_table_exists_with_correct_schema(self, db):
        """Verify fair_selection_state table created with correct columns and types."""
        result = db.session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'fair_selection_state'
                ORDER BY ordinal_position
            """)
        ).fetchall()

        actual_cols = {row[0]: (row[1], row[2]) for row in result}

        expected_cols = {
            "id": ("uuid", "NO"),
            "pipeline": ("character varying", "NO"),
            "entity_id": ("uuid", "NO"),
            "phase": ("integer", "NO"),
            "coverage_bitmap": ("bigint", "NO"),
            "updated_at": ("timestamp with time zone", "NO"),
        }

        assert actual_cols == expected_cols, f"Expected {expected_cols}, got {actual_cols}"

    def test_fair_selection_state_unique_constraint_exists(self, db):
        """Verify unique constraint on (pipeline, entity_id) prevents duplicates."""
        result = db.session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'fair_selection_state' AND constraint_type = 'UNIQUE'
            """)
        ).fetchall()

        constraint_names = {row[0] for row in result}
        assert "uq_fair_selection_state_entity" in constraint_names

    def test_fair_selection_state_index_exists(self, db):
        """Verify index on (pipeline, entity_id) for query performance."""
        result = db.session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'fair_selection_state'
            """)
        ).fetchall()

        index_names = {row[0] for row in result}
        assert "ix_fair_selection_state_pipeline_entity" in index_names

    def test_phase_column_exists_on_all_task_tables(self, db):
        """Verify phase column added to all task tables."""
        for table_name in ["translation_task", "snapshot_translation_task", "embedding_task", "discovery_task"]:
            result = db.session.execute(
                text(f"""
                    SELECT data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = 'phase'
                """)
            ).fetchone()

            assert result is not None, f"phase column missing from {table_name}"
            assert result[0] == "integer", f"phase column wrong type in {table_name}"
            assert result[1] == "NO", f"phase column nullable in {table_name}"


class TestOrmModelsReflectPhase:
    """Test ORM models properly map phase column."""

    def test_translation_task_phase_persists(self, db):
        """Verify TranslationTask.phase roundtrips to database."""
        from app.models.translation import TranslationTask

        task = TranslationTask(
            id="10000000-0000-0000-0000-000000000001",
            candidate_id="20000000-0000-0000-0000-000000000001",
            locale="fr",
            source_hash="abc123",
            phase=1,
        )
        db.session.add(task)
        db.session.commit()

        retrieved = db.session.query(TranslationTask).filter_by(locale="fr").first()
        assert retrieved.phase == 1

    def test_embedding_task_phase_persists(self, db):
        """Verify EmbeddingTask.phase roundtrips to database."""
        from app.models.search import EmbeddingTask

        task = EmbeddingTask(
            id="30000000-0000-0000-0000-000000000001",
            candidate_id="20000000-0000-0000-0000-000000000001",
            model="embedding-v1",
            locale="de",
            text_hash="hash123",
            phase=1,
        )
        db.session.add(task)
        db.session.commit()

        retrieved = db.session.query(EmbeddingTask).filter_by(model="embedding-v1").first()
        assert retrieved.phase == 1


class TestBackfillLogic:
    """Test backfill populates fair_selection_state correctly."""

    def test_backfill_creates_one_state_row_per_entity(self, db):
        """Verify backfill inserts exactly one row per pipeline entity."""
        # This test assumes backfill has already run (by migration).
        # Setup: insert mock tasks
        from app.models.translation import TranslationTask
        from app.models.search import EmbeddingTask

        candidate_id_1 = "30000000-0000-0000-0000-000000000001"
        candidate_id_2 = "30000000-0000-0000-0000-000000000002"

        task1 = TranslationTask(
            id="40000000-0000-0000-0000-000000000001",
            candidate_id=candidate_id_1,
            locale="fr",
            source_hash="hash1",
        )
        task2 = TranslationTask(
            id="40000000-0000-0000-0000-000000000002",
            candidate_id=candidate_id_1,
            locale="it",
            source_hash="hash1",
        )
        task3 = TranslationTask(
            id="40000000-0000-0000-0000-000000000003",
            candidate_id=candidate_id_2,
            locale="es",
            source_hash="hash2",
        )

        db.session.add_all([task1, task2, task3])
        db.session.commit()

        # Query backfilled state
        result = db.session.execute(
            text("""
                SELECT COUNT(DISTINCT entity_id)
                FROM fair_selection_state
                WHERE pipeline = 'translation'
            """)
        ).scalar()

        assert result == 2, f"Expected 2 unique translation entities, got {result}"
```

**Refactor: Test suite audit**

- ✅ Each test has one concern: schema existence, constraints, ORM mapping, backfill logic.
- ✅ No redundant assertions; each test targets one piece of contract.
- ✅ Happy path tests verify full contract; negative path test verifies rollback.
- ✅ Table and column names are precise, not wildcarded.
- ✅ ORM tests use actual model classes (import from `app.models`), ensuring mapping is real.

---

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| fair_selection_state table | `test_fair_selection_state_table_exists_with_correct_schema` | `test_fair_selection_state_duplicate_entity_rejected` |
| phase column on tasks | `test_phase_column_exists_on_all_task_tables` | `test_phase_column_not_null_enforced` |
| ORM model mapping | `test_orm_models_reflect_phase_column` | `test_orm_validation_rejects_invalid_phase` |
| backfill idempotence | `test_backfill_populates_fair_selection_state` | `test_backfill_idempotent_on_rerun` |
| schema constraints & indices | `test_schema_satisfies_fair_selection_requirements` | `test_migration_rollback_removes_schema_changes` |

---

## Review gate

Before merging:

1. **Red tests pass**: All 10 test descriptions (5 slices × 2 paths) are written, run, and fail for the right reason.
2. **Green implementation passes**: Migration runs cleanly; backfill completes without errors.
3. **Refactor audit complete**: Each slice reports extraction candidates or "no refactor needed" with justification.
4. **Local gate passes**: `pytest tests/features/fair_selection/test_schema.py -v` exits 0; all tests green.
5. **Full suite passes**: `scripts/ci.sh` exits 0 (or project's standard CI entry point).
6. **Migration rollback verified**: Manual or automated downgrade test passes; schema rolls back cleanly.
7. **No broken dependencies**: ORM models compile; imports resolve; no dangling references.

---

## Out of scope

- **State transition logic** (C3)
- **Priority calculation changes** (C4–C7)
- **Worker integration** (C8)
- **Phase-aware query optimization** (defer to C3–C8)
- **Backfill for new tasks** (C3 adds trigger or enqueue handler)

---

## Verification

```bash
# Run from the repository root.

# Run C2 schema tests only
pytest tests/features/fair_selection/test_schema.py -v

# Verify migration can be applied and rolled back
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Full CI suite
scripts/ci.sh
```

Expected:
- All 10 tests in `test_schema.py` pass (happy + negative paths).
- Migrations apply cleanly; downgrades cleanly.
- `ci.sh` exits 0; no regressions in existing tests.
- ORM models load without errors; no import or syntax issues.

---

## Refactor report

**Slice 1 (fair_selection_state table & index):**
✅ Index strategy reviewed; combined `(pipeline, entity_id)` index is sufficient. No extraction needed; one table, one index, one constraint.

**Slice 2 (phase column on tasks):**
✅ Combined into single migration file for atomicity. Four identical `add_column` calls are acceptable (boilerplate, not logic extraction). No extraction needed.

**Slice 3 (ORM model updates):**
✅ Four identical column mappings (one per task model). No validation logic added; defer to C3 if validators are needed. No extraction needed.

**Slice 4 (backfill):**
✅ Four SQL INSERT statements (one per pipeline). Each has distinct table and entity_id column; combined loop would obscure difference. No extraction needed.

**Slice 5 (test suite):**
✅ No redundant test logic. Each test class has one concern (schema, ORM, backfill). No extraction candidates.

---

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c2-schema-migration`.
- Commit the red tests first (all 10 test descriptions in `tests/features/fair_selection/test_schema.py`), then the green change (migration + ORM updates).
- Run the local gate on the chapter branch: `pytest tests/features/fair_selection/test_schema.py -v && scripts/ci.sh`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
