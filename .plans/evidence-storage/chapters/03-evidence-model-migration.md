---
name: "Chapter 3 — Evidence model and migration"
overview: "evidence table keyed to a suggestion, with kind, storage key, hash, size, source URL and both fetched_at and created_at timestamps, plus a reversible migration."
todos:
  - id: model
    content: "Evidence model and EvidenceKind enum"
    status: pending
  - id: migration
    content: "Alembic revision with cascade delete and dedupe constraint"
    status: pending
isProject: false
---

# Chapter 3 — Evidence model and migration

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/evidence-model` · **Status:** planned

**Depends on:** [suggestion-interface 1](../../suggestion-interface/chapters/01-suggestion-model-migration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Storage for the metadata half of an evidence record (architecture §4); the object store holds the bytes.

## Design decisions

**`ondelete=CASCADE` on `suggestion_id`**: evidence has no independent meaning once its suggestion is gone
(unlike users/keys on suggestions, D7 — evidence belongs to the suggestion, not to an account). Deleting a
suggestion row (not expected in normal operation, but possible via an admin script) removes its evidence
rows; a documented follow-up (open seam) is sweeping the now-orphaned objects.

**Dedupe constraint** `uq_evidence_suggestion_sha256` on (`suggestion_id`, `sha256`) enforces D3 at the
database level, not just in service logic.

**`fetched_at` is nullable at the column level but required by the service** (chapter 4): the column stays
nullable so a future kind (e.g. a manually attached file with no known capture time) is not blocked by a
schema change; today's only writer always supplies it.

**Conventions**: UUID key, native enum `evidence_kind`, named constraints, `server_default=func.now()` for
`created_at`, matching [20260625_taxonomy.py](../../../apps/api/alembic/versions/20260625_taxonomy.py).
Revision `<yyyymmdd>_evidence`, chained off the current single head.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/evidence.py`, `apps/api/app/models/__init__.py` | Model, `EvidenceKind` |
| `apps/api/alembic/versions/<yyyymmdd>_evidence.py` | Migration |
| `apps/api/tests/test_evidence_model.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `Evidence · persists with a generated id and server-set created_at` | Round trip |
| `Evidence · rejects a duplicate sha256 for the same suggestion` | Unique constraint |
| `Evidence · allows the same sha256 for a different suggestion` | Negative pair |
| `Evidence · deleting the suggestion deletes its evidence` | Cascade |
| `Evidence · rejects an unknown kind` | Enum |
| `Evidence · byte_size and content_type are required` | Not-null |

## Green

1. Model and enum; tests 1, 5, 6.
2. Unique constraint; tests 2–3.
3. Cascade; test 4.
4. Migration and round trip.

## Refactor gate

Model file ≤ ~100 LOC. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_evidence_model.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Object store interaction (chapter 4), endpoints.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-model
```

```text
test(api): describe evidence constraints and cascade delete

feat(api): add evidence model and migration
```
