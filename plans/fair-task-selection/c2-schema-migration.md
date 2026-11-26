---
id: C2
depends_on: []
touches:
  - apps/api/migrations/
  - apps/api/app/models/
  - tests/
execution: chapter-implementer
---

# C2: Database Schema & Migration

## Goal

Create the `fair_selection_state` table, add `phase` column to task tables, and write migration scripts. Schema enables state tracking for C3–C10.

## Acceptance Criteria

- ✅ Migration script creates `fair_selection_state` table with correct schema
- ✅ `phase` columns added to `translation_task`, `snapshot_translation_task`, `embedding_task`, `discovery_task`
- ✅ Indices created for query performance (entity_id + pipeline lookup)
- ✅ Backfill script populates initial state (all existing tasks → phase 1)
- ✅ SQLAlchemy ORM models updated
- ✅ Migration runs and rolls back cleanly

## Scope

**What's in C2:**
- Alembic migration file(s)
- ORM model updates (SQLAlchemy)
- Backfill SQL
- Schema tests (happy + negative paths)

**What's NOT in C2:**
- State transition logic (C3)
- Priority calculation changes (C4–C7)
- Worker integration (C8)

## Implementation Plan

### Slice 1: `fair_selection_state` Table & Index

**Red**: Two tests:

1. **Happy path**: Table exists with correct schema
   - Create table, run migration
   - Query: `SELECT * FROM fair_selection_state` → table exists, columns are correct
   - Assert: `id` (UUID), `pipeline` (TEXT), `entity_id` (UUID), `phase` (INT), `coverage_bitmap` (BIGINT), `updated_at` (TIMESTAMP)

2. **Negative path**: Duplicate insert rejected
   - Insert row: `(id=X, pipeline='translation', entity_id=Y, phase=1)`
   - Try insert duplicate: `(id=X, pipeline='translation', entity_id=Y, phase=1)`
   - Assert: Unique constraint violation (or ON CONFLICT IGNORE)

**Green**: Alembic migration file:

```python
# migrations/versions/001_create_fair_selection_state.py

def upgrade():
    op.create_table(
        'fair_selection_state',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('pipeline', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('phase', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('coverage_bitmap', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_fair_selection_state_entity',
        'fair_selection_state',
        ['pipeline', 'entity_id']
    )
    op.create_index(
        'ix_fair_selection_state_pipeline_entity',
        'fair_selection_state',
        ['pipeline', 'entity_id']
    )

def downgrade():
    op.drop_table('fair_selection_state')
```

**Refactor**: Check index strategy; consider partial index on `phase < 3` for faster query on active phases.

### Slice 2: Add `phase` Column to Task Tables

**Red**: Two tests:

1. **Happy path**: Phase column exists on all task tables with default=1
   - Query: `SELECT phase FROM translation_task LIMIT 1` → column exists, value=1 (default)
   - Assert: Existing tasks have phase=1 (not NULL)

2. **Negative path**: Null phase is rejected
   - Try: `INSERT INTO translation_task (..., phase=NULL, ...)`
   - Assert: NOT NULL constraint violation

**Green**: Migration script adds column to four tables:

```python
# In same migration file (001_create_fair_selection_state.py) or separate (002_add_phase_to_tasks.py)

def upgrade():
    for table in ['translation_task', 'snapshot_translation_task', 'embedding_task', 'discovery_task']:
        op.add_column(table, sa.Column('phase', sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    for table in ['translation_task', 'snapshot_translation_task', 'embedding_task', 'discovery_task']:
        op.drop_column(table, 'phase')
```

**Refactor**: Combine into one migration file if feasible (fewer round-trips); verify no schema conflicts.

### Slice 3: SQLAlchemy ORM Model Updates

**Red**: Two tests:

1. **Happy path**: ORM model reflects schema
   - Create instance: `task = DiscoveryTask(..., phase=1)`
   - Assert: `task.phase == 1`
   - Save and retrieve: Assert phase persisted

2. **Negative path**: Invalid phase value caught
   - Try: `task.phase = 999` (invalid phase)
   - Assert: Either validation error or allowed (design decision: should we enforce 0–2?)

**Green**: Update models:

```python
# apps/api/app/models/discovery/discovery_task.py

class DiscoveryTask(Base):
    # ... existing columns ...
    phase: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

# apps/api/app/models/translation.py

class TranslationTask(Base):
    # ... existing columns ...
    phase: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

# ... similar for SnapshotTranslationTask, EmbeddingTask
```

Add Pydantic validator (optional):

```python
@field_validator('phase')
@classmethod
def validate_phase(cls, v):
    if v not in (1, 2, 3):
        raise ValueError(f'Phase must be 1–3, got {v}')
    return v
```

**Refactor**: Check if validators needed; defer to C3 if business logic is complex.

### Slice 4: Backfill Script

**Red**: Two tests:

1. **Happy path**: Backfill populates `fair_selection_state` for all existing entities
   - Setup: 100 existing translation tasks (10 candidates × 10 locales)
   - Run backfill
   - Query: `SELECT COUNT(*) FROM fair_selection_state WHERE pipeline='translation'` → returns 10 (one row per candidate)
   - Assert: All have phase=1, coverage_bitmap=0

2. **Negative path**: Backfill doesn't duplicate rows if re-run
   - Run backfill, then run again
   - Assert: Still 10 rows, no duplicates

**Green**: Write backfill SQL (or Python script):

```sql
-- Migration: backfill fair_selection_state for translation candidates

INSERT INTO fair_selection_state (pipeline, entity_id, phase, coverage_bitmap)
SELECT DISTINCT 'translation', candidate_id, 1, 0
FROM translation_task
WHERE candidate_id NOT IN (
    SELECT entity_id FROM fair_selection_state WHERE pipeline = 'translation'
);

-- Similar for snapshot_translation_task (using catalogue_service_id), embedding_task (candidate_id), discovery_task (catalogue_service_id)
```

Alternatively, write Python using SQLAlchemy (in migration context manager).

**Refactor**: Check for existing entries before inserting (idempotent).

### Slice 5: Schema Test Suite

**Red**: Two tests:

1. **Happy path**: Schema validation test passes
   - Create test database, run all migrations
   - Verify all tables, columns, indices exist
   - Assert: `fair_selection_state` has correct schema; `phase` columns in task tables

2. **Negative path**: Migration rollback works
   - Upgrade, then downgrade
   - Assert: Tables removed; `fair_selection_state` doesn't exist

**Green**: Write test file:

```python
# tests/features/fair_selection/test_schema.py

def test_fair_selection_state_table_exists(db):
    """Verify fair_selection_state table created with correct columns."""
    # Query table info
    result = db.session.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'fair_selection_state'
    """)).fetchall()

    expected_cols = {
        'id': 'uuid',
        'pipeline': 'character varying',
        'entity_id': 'uuid',
        'phase': 'integer',
        'coverage_bitmap': 'bigint',
        'updated_at': 'timestamp without time zone'
    }

    actual = {row[0]: row[1] for row in result}
    assert actual == expected_cols, f"Expected {expected_cols}, got {actual}"

def test_phase_column_defaults_to_one(db):
    """Verify new translation_task rows get phase=1."""
    task = TranslationTask(candidate_id=..., locale='en', status='PENDING')
    db.session.add(task)
    db.session.commit()

    retrieved = db.session.query(TranslationTask).first()
    assert retrieved.phase == 1

def test_migration_rollback(db):
    """Verify downgrade removes fair_selection_state table."""
    # This is integration test; depends on alembic context
    pass
```

**Refactor**: Schema tests are minimal; check if any duplication with ORM tests (defer complex ORM validation to C3–C8).

## Test Output

**After this chapter**:
- Migration file(s): `/apps/api/migrations/versions/00X_*.py`
- Updated ORM models: `app/models/{discovery,translation,search}.py`
- Test file: `tests/features/fair_selection/test_schema.py`

## Gate

✅ Local: `pytest tests/features/fair_selection/test_schema.py` (all 5 slices)
✅ Full: `scripts/ci.sh` (overall)

## Notes

- Backfill runs as part of migration (via `op.execute()` or separate script invoked by CI)
- Phase column not yet used in queries (C3–C8 add that logic)
- If existing tables have triggers or constraints, review migration script for compatibility
- Consider index strategy: `fair_selection_state` queries are `WHERE pipeline=? AND entity_id=?` (covered by combined index)
