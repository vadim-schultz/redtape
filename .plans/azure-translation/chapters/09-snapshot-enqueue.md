---
name: "Chapter 09 — Snapshot enqueue, refresh and backfill"
overview: "Create snapshot translation tasks when a mention makes a page relevant, ordered by the highest confidence on that page. Refresh only pages already translated when a new snapshot arrives. Backfill the existing pages, idempotently. Pages with no candidates cost nothing."
id: AZ09
depends_on:
  - AZ08
touches:
  - apps/api/app/features/translation/snapshot_enqueue.py
  - apps/api/app/features/translation/enqueue.py
  - apps/api/app/features/discovery/candidate_service.py
  - apps/api/app/features/discovery/artifact_upload.py
  - apps/api/app/features/discovery/dependencies.py
  - apps/api/scripts/backfill_snapshot_translations.py
  - apps/api/tests/
execution: chapter-implementer
---

# Chapter 09 — Snapshot enqueue, refresh and backfill

**Repo:** `redtape` (`apps/api`) · **Depends on:** [Chapter 08](08-snapshot-machine-api.md) · **Decisions:** [D1](../gaps-and-decisions.md#d1--the-document-unit-is-the-procedure-page-keyed-per-page), [D7](../gaps-and-decisions.md#d7--eager-queue-driven-translation-reads-never-translate) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Tasks for pages appear when a candidate's mention makes the page relevant, and a new snapshot refreshes only pages that were already translated or are queued. The backfill covers existing pages and can be re-run safely.

## Scope

- In: the enqueue service, the mention hook, the upload listener, the backfill script.
- Out: the worker (11), the public read (12), the cleaned-text short-circuit (11).

## Design

1. **Mention hook.** `CandidateService.record_mentions` already calls `TranslationEnqueuer.enqueue_many(candidate_ids)` after the search text refresh. That call is extended with the page facts it already has: for each recorded mention, the catalogue row and the candidate's confidence. The constructor of `CandidateService` does not change.
2. **Enqueue rule.** For each page touched by the mentions, one pending task per target locale (`en tr ru uk pl ro`), with priority from the highest confidence among the candidates on that page. The upsert is hash-aware and idempotent, so a second candidate on the same page adds no second task. A page whose current snapshot translation already matches the latest sha enqueues nothing.
3. **Upload listener.** `ArtifactUploadService.__init__(repository, store, *, max_bytes)` is at three parameters. Discovery defines a `SnapshotStoredListener` protocol with one method, `snapshot_stored(catalogue_service_id, artifact_sha256)`, and an `UploadPolicy` dataclass that bundles `max_bytes` and the listener. The service then takes `(repository, store, policy)`. The translation feature implements the listener. Only `discovery/dependencies.py` imports translation.
4. **Refresh rule.** On a new `html_snapshot` row, the listener refreshes only a page that has a `snapshot_translation` row or an open task. A page with no candidates and no translation enqueues nothing. A repeated sha (the upload returns the existing row) does nothing.
5. **Backfill.** `apps/api/scripts/backfill_snapshot_translations.py` walks catalogue rows that have a latest snapshot, with flags `--after`, `--batch-size`, `--locale` and the DB soft-limit stop used by `backfill_translations.py`. It commits per batch and prints missing, stale and current counts before it writes.
6. **Layering.** The translation enqueue service uses discovery's public read methods only. It never imports discovery repositories.

## Files

| Path | Change |
| --- | --- |
| `translation/snapshot_enqueue.py` (new) | page enqueue and refresh rules |
| `translation/enqueue.py` | `enqueue_many` takes the page facts too |
| `discovery/candidate_service.py` | pass page facts from `record_mentions` |
| `discovery/artifact_upload.py` | `UploadPolicy` and the listener call |
| `discovery/dependencies.py` | wire the translation listener |
| `scripts/backfill_snapshot_translations.py` (new) | backfill |
| `apps/api/tests/test_snapshot_enqueue*.py` (new) | enqueue, refresh and backfill tests |

## Red tests

**Happy path**
- `Mention hook · recording a mention enqueues one snapshot task per target locale, with the highest confidence on the page as priority`
- `Mention hook · a second candidate on the same page adds no second task`
- `Upload · a new snapshot for a translated page refreshes its tasks to pending`
- `Backfill · a dry run counts missing, stale and current pages and writes nothing`
- `Backfill · a second run resumes after --after and enqueues nothing new`

**Negative path**
- `Mention hook · a page whose current snapshot translation matches the latest sha enqueues nothing`
- `Upload · a new snapshot for a page with no candidates and no translation enqueues nothing`
- `Upload · an identical sha returns the existing row and enqueues nothing`
- `Layering · no discovery module imports a translation repository (import test)`
- `Config · with no target locales, nothing is enqueued`

## Green

The smallest change for each red test. Start with the upload policy refactor, behind the existing tests, so the constructor change is a green step of its own.

## Refactor gate

- `ArtifactUploadService` stays at three parameters; the policy bundles the rest.
- The page enqueue is one function per rule (enqueue, refresh, skip), not a chain of conditions.
- `CandidateService` keeps its constructor. Do not add a fifth dependency.
- House rules: about 5 lines per function, one nesting level, no boolean flags.

## Verification

```bash
cd apps/api
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_snapshot_enqueue*.py tests/test_artifact_upload*.py tests/test_candidate_*.py tests/test_discovery_*.py
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_architecture*.py
cd ../.. && ./ci.sh
```

## Out of scope

The cleaned-text hash and the zero-character path (11), the public read (12), any worker change.

## Operator steps after merge

After the worker in chapter 11 is verified: run `scripts/backfill_snapshot_translations.py` with a dry run first, then in batches. Until then no snapshot tasks exist, except those created by new mentions.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-09-snapshot-enqueue
# test(api): ... (red), refactor(api): upload policy (green), feat(api): ... (green), feat(api): backfill
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
