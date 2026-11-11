---
name: "Chapter 08 — Snapshot machine API"
overview: "Give the translation worker machine routes for snapshots: claim by reference, complete with translated blocks or an unchanged or skipped outcome, fail, release, and summary. The lease, stale and no-attempt rules are the card path's, and the object store is written only by the API."
id: AZ08
depends_on:
  - AZ07
touches:
  - apps/api/app/features/translation/snapshot_queue.py
  - apps/api/app/features/translation/snapshot_completion.py
  - apps/api/app/features/translation/snapshot_store.py
  - apps/api/app/features/translation/snapshot_checks.py
  - apps/api/app/features/translation/snapshot_machine_controller.py
  - apps/api/app/features/translation/router.py
  - apps/api/app/schema/translation/snapshot_machine.py
  - apps/api/tests/fixtures/discovery_machine_contract.json
  - apps/api/tests/
execution: chapter-implementer
---

# Chapter 08 — Snapshot machine API

**Repo:** `redtape` (`apps/api`) · **Depends on:** [Chapter 07](07-snapshot-schema.md) · **Decisions:** [D6](../gaps-and-decisions.md#d6--snapshot-translations-are-blocks-of-text-not-markup), [D7](../gaps-and-decisions.md#d7--eager-queue-driven-translation-reads-never-translate) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

The worker can claim snapshot tasks, read them by reference, post the result, fail or release them, and read a summary, all under the same guard as the card routes. Workers never write the object store; the API does.

## Scope

- In: routes, schemas, store, completion, checks, the contract fixture.
- Out: fetching the page and translating it (11), enqueue and hooks (09), the public read (12).

## Design

1. **Routes** under the same machine prefix as the card routes, guarded by `require_discovery_machine`:
   - `POST /snapshots/claim` with `limit` (at most 5). Each item carries `task_id`, `catalogue_service_id`, `locale`, `source_locale` (`de`), `artifact_id`, `artifact_sha256`, `source_url`, `stored_source_hash` (nullable) and `lease_expires_at`.
   - `POST /snapshots/complete` with at most 5 items. Each item carries `task_id`, `artifact_sha256` (the one claimed), `source_hash`, and an `outcome` of `translated`, `unchanged` or `skipped`. A translated item also carries `blocks`, `truncated`, `engine`, `model`.
   - `POST /snapshots/fail` and `POST /snapshots/release`, as for cards.
   - `GET /snapshots/summary`: counts per locale of pending, claimed, failed, translated, stale and skipped.
2. **Claim stamps the snapshot.** The latest `html_snapshot` of the catalogue row is resolved through the discovery artifact service's public method. The translation service never reads the discovery repository. The task's `artifact_id` and `artifact_sha256` are written at claim time. If no snapshot exists, the task fails with `no_snapshot`.
3. **Complete**, per item:
   - If `artifact_sha256` no longer matches the latest snapshot, the answer is `stale` and the task is requeued (`Settlement.REQUEUE`), as the card path does.
   - `unchanged` requires `source_hash` to equal the stored one. Only `artifact_sha256` is updated, and no object is written. The answer is `unchanged`.
   - `translated` validates the blocks, writes the object at `translations/v1/snapshots/{catalogue_service_id}/{locale}/{content_sha256}.json` through `SnapshotStore`, then updates the index row. The replaced object is deleted after commit, through the deferred-delete helper the card path uses. The answer is `stored`.
   - `skipped` writes the marker row with `skipped_reason` and completes the task.
   - If the object store is unavailable, the answer is `unavailable` and the task is released without an attempt, as the card path does.
4. **Validation.** Block kinds come from the fixed set `h1`–`h6`, `p`, `li`, `row`, `dt`. A `row` carries `cells`; the others carry `text`. A block over 4,000 characters, or more than 2,000 blocks, is `rejected`. The body is capped by `MAX_BODY_BYTES` (2 MiB, `schema/translation/machine.py`), which is why a complete request carries at most 5 items.
5. **Store.** `SnapshotStore` mirrors `TranslationPayload`, with `unit: "snapshot"`, canonical sorted-key JSON, and `source_hash`, `truncated`, `source_url`, `blocks`. The card store's `Literal["card"]` is not widened.
6. **Contract.** Routes and schemas change the machine contract, so the fixture is regenerated.

## Files

| Path | Change |
| --- | --- |
| `translation/snapshot_queue.py` (new) | claim and stamp |
| `translation/snapshot_completion.py` (new) | complete by outcome |
| `translation/snapshot_store.py` (new) | object payload and writes |
| `translation/snapshot_checks.py` (new) | stale and validation checks |
| `translation/snapshot_machine_controller.py` (new) | routes |
| `translation/router.py` | mount the routes |
| `schema/translation/snapshot_machine.py` (new) | request and response schemas |
| `apps/api/tests/fixtures/discovery_machine_contract.json` | regenerated |
| `apps/api/tests/test_snapshot_machine*.py` (new) | route tests |

## Red tests

**Happy path**
- `Claim · returns references, stamps artifact_id and sha onto the task, and carries stored_source_hash`
- `Complete · translated stores the object and updates the index row; answer stored`
- `Complete · unchanged completes with no object write; answer unchanged`
- `Complete · skipped writes the marker row and completes the task`
- `Summary · counts per locale for each status`

**Negative path**
- `Complete · a stale artifact_sha256 answers stale and requeues the task; nothing is stored`
- `Complete · an unavailable object store answers unavailable and releases the task without an attempt`
- `Claim · a catalogue row with no snapshot fails the task with no_snapshot`
- `Complete · a block over 4,000 characters answers rejected`
- `Complete · a sixth item in one request is refused with 422`
- `Auth · a wrong API key is refused with 401`
- `Complete · a completed task cannot be completed again`

## Green

The smallest change for each red test, starting with the claim route.

## Refactor gate

- Dispatch by outcome through a small handler table, not an if-chain. The rule of three applies here.
- Completion code stays under about 100 lines per file; each handler is a function of about 5 lines.
- No route module holds SQL. The controller calls the service; the service calls the repository.
- House rules: at most 3 parameters, no `Any`, docstrings.

## Verification

```bash
cd apps/api
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_snapshot_machine*.py tests/test_translation_machine*.py tests/test_machine_contract_fixture.py tests/test_api_contract.py
.venv/bin/python -m scripts.export_machine_contract
cd ../discovery-ingest && .venv/bin/python -m pytest -q tests/test_api_contract.py
cd ../.. && ./ci.sh
```

## Out of scope

Enqueue and the mention hook (09), fetching and translating pages (11), the public read and its ETag (12).

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-08-snapshot-machine-api
# test(api): ... (red), feat(api): ... (green), refactor(api): ... (gate), feat(ingest): contract mirror if needed
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
