---
name: "Chapter 1 — Representative row end-to-end smoke"
overview: "Trace one GovData or PVOG catalogue row through task drain, FIM enrichment, T3/T4 inspection, emit preview, and one pending suggestion."
todos:
  - id: select-row
    content: "Select a source row with a portal URL and, preferably, a FIM identifier"
    status: pending
  - id: drain-enrich
    content: "Drain the row's fetch and enrich tasks and record outcomes"
    status: pending
  - id: verify-emit
    content: "Verify T3/T4, inspect preview, and emit exactly one row"
    status: pending
  - id: negative-paths
    content: "Record failed-fetch and invalid-enrichment outcomes"
    status: pending
isProject: false
---

# Chapter 1 — Representative row end-to-end smoke

**Repo:** `redtape` · **Branch:** `feat/discovery-operations-row-smoke` · **Status:** partial — fixture-backed verification complete; cross-stage operator smoke blocked

**Depends on:** [discovery-layer](../../discovery-layer/01-rollout.md), [discovery-online](../../discovery-online/01-rollout.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/discovery-operations`

## Goal

Prove the complete currently supported discovery path with one carefully selected catalogue row:

```text
GovData/PVOG ingest
  → catalogue row and task
  → fetch/enrich drain
  → entity and claims
  → T3/T4 pipeline inspection
  → emit preview
  → one pending suggestion
```

This chapter is an operator smoke, not a crawler implementation. It must not introduce Playwright, screenshot capture, evidence upload, broad link discovery, or automatic emit.

## Row selection

Prefer a `govdata` row with:

- a valid `portal_url`, so the initial `fetch_url` task is created;
- a source-native `fim_id` in `raw_payload`, so the fanout policy creates an `enrich_metadata` task;
- a stable title and jurisdiction accepted by the machine API.

If a PVOG row is used, record whether it has an equivalent FIM identifier. A row without `portal_url` is a valid T0 boundary case but cannot prove the fetch path. A row without an enrichment identifier cannot prove automatic FIM enrichment and must be labelled as a partial smoke.

## Operator sequence

1. Confirm the target API, machine key, admin session, discovery enablement, and jurisdiction ID. Never print or commit the API key.
2. Ingest one fixture row locally or use a bounded live ingest through the existing CLI:

   ```bash
   python -m discovery_ingest govdata run \
     --input <fixture.json> \
     --jurisdiction-id <jurisdiction-uuid>
   ```

   For the scheduled production path, use the documented GitHub Actions discovery dispatch and its bounded GovData/PVOG page limits. Do not run a laptop process against production as the normal operating path.
3. Locate the returned `catalogue_service_id` and inspect `/admin/discovery/catalogue`. Confirm the row is present, the source and external ID are stable, and the initial task fanout is visible.
4. Inspect `/admin/discovery/tasks` for the selected catalogue ID or query the admin task API. Record the `fetch_url` and `enrich_metadata` task IDs, statuses, targets, priorities, and lease values.
5. Run one bounded worker drain:

   ```bash
   python -m discovery_ingest worker drain --max-tasks 50
   ```

   Record the JSON report. The current implementation may complete the fetch task and the FIM enrichment task in the same batch, depending on queue ordering.
6. Open `/admin/discovery/pipeline/<catalogue-service-id>` or `GET /api/v1/discovery/admin/catalogue/<catalogue-service-id>/pipeline`. Confirm:
   - fetch logs contain HTTP metadata or an explicit error;
   - FIM enrichment created one normalized entity;
   - claims contain the expected metadata and/or `new_document` payload;
   - events show the corresponding lineage.
7. Verify stage progression. A row with a portal task should be at least T1 after ingest; a fetch log makes it T2; claims make it T3; valid emit-eligible claims make it T4. A T4 row is ready, not yet emitted.
8. Open the emit preview and confirm that:
   - `new_document` claims have `title_i18n` and `official_url`;
   - metadata is marked `metadata_not_emitted`;
   - unresolved requirements are marked `unresolved_requirement_documents`;
   - no unexpected claim is silently omitted.
9. Emit exactly one selected catalogue row through the machine endpoint:

   ```text
   POST /api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit
   ```

   Record `created_count`, `skipped_count`, `replayed_count`, and the returned suggestion ID. Verify that the suggestion is `pending`; do not vote or promote it in this chapter.
10. Re-open the pipeline and record that the row remains T4. Replaying emit must be idempotent and must not create a second suggestion for the same claim.

## Negative paths

Record both failure scenarios in the smoke evidence:

- **Failed fetch:** use a controlled invalid or unreachable target in a fixture/local environment. The worker must record a fetch attempt, mark the task `failed`, preserve `last_error`, and return a report that identifies the failure. It must not create claims from an unsuccessful fetch.
- **Invalid FIM enrichment:** use a response missing `leistungsschluessel`, invalid JSON, or a non-success HTTP response. The worker must fail the enrichment task explicitly, avoid partial claim success, and leave the row below T4 unless another valid claim path exists.

Do not manufacture a production failure to satisfy the negative path. Use existing fixtures, a local test server, or a documented API mock.

## Execution record — 2026-10-22

This pass used repository fixtures and mock transports only. It did not call GovData, PVOG, FIM,
Render, or a production admin surface, and it did not print or create an API key.

### Selected row

The representative ingest fixture is the first row in
`apps/discovery-ingest/tests/fixtures/govdata/ozg_page.json`:

- source: `govdata`;
- external ID: `govdata:leika:12345678901234`;
- jurisdiction: `11111111-1111-1111-1111-111111111101`;
- title: `Beispiel-Leistung`;
- portal URL: `https://example.bund.de/leistung`;
- raw payload identifiers: `ozgid=OZ-EXAMPLE-001`, `leika_key=12345678901234`.

The row has a portal URL, but its raw payload has no `fim_id`. It therefore proves the ingest and
fetch boundary only; it is a partial smoke and cannot prove automatic FIM fanout for this exact row.

### Fixture and API evidence

The following checks passed:

- `cd apps/discovery-ingest && uv run pytest -q --tb=short tests/test_govdata_client.py tests/test_govdata_cli.py tests/test_pvog_cli.py tests/test_worker_drain.py tests/test_enrich_metadata_worker.py` — **14 passed**.
- The GovData CLI test posts the selected fixture shape to `/api/v1/discovery/machine/catalogue/batch`, preserves the source/external ID, and sends a non-secret mock `X-API-Key`.
- The successful fetch mock records a `200` HTML fetch log and completes its `fetch_url` task. The worker and enrich tests use mocked catalogue ID `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb`; these IDs are test fixtures, not IDs returned by the selected GovData row.
- The successful FIM mock serves `LB-EXAMPLE-STECK`, then the worker posts one entity and at least one claim and completes the `enrich_metadata` task.
- `docker compose up -d --wait db` produced a healthy local PostgreSQL container. With that local database,
  `cd apps/api && REQUIRE_DB=1 DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape PYTHONPATH=. uv run pytest -q --tb=short tests/test_discovery_pipeline.py tests/test_discovery_emit_preview.py tests/test_discovery_emit.py` — **11 passed**.
- The API tests verify T0/T1/T2 stage derivation, `new_document` preview payload mapping, the
  `unresolved_requirement_documents` skip reason, one pending suggestion, and idempotent replay.

### Negative-path evidence

- **Failed fetch:** `test_worker_drain_marks_fail_when_get_times_out` makes the portal request raise
  `httpx.ReadTimeout`. The worker posts a fetch log with `http_status=null` and an error, marks the
  task failed with a non-empty error, and reports `failed=1`; no entity/claim request is accepted by
  the mock.
- **Invalid FIM enrichment:** `test_enrich_metadata_fails_task_when_steckbrief_404` returns HTTP
  `404` for the FIM steckbrief. The worker reports `failed=1`, posts one explicit task failure with
  a non-empty error, and does not accept a partial entity/claim write.

### Unverified boundary and blocker

No persisted catalogue service ID, task IDs, drain JSON report, admin pipeline response, T4 stage,
or emitted suggestion ID can be recorded for the selected GovData row: no local API server/admin
session was started, and no authorized target API/key/session was provided. The API tests above use
synthetic database rows to verify the downstream contracts; they do not turn the selected fixture
into a persisted end-to-end row. The next smoke must provide a local API session plus a fixture row
with a `fim_id` (or an equivalent controlled FIM mock) before claiming complete T4/manual-emit
coverage.

## Evidence to record

- source, external ID, catalogue service ID, and jurisdiction;
- task IDs and before/after statuses;
- worker drain JSON report;
- fetch-log status and error fields;
- entity and claim counts;
- derived stage and emit-preview skip reasons;
- emitted suggestion ID and pending status;
- negative-path task errors and confirmation of no unintended suggestion.

Red/green implementation is not required for this docs-only operator chapter. If the sequence exposes a missing API or worker capability, stop the smoke, document the gap, and route the implementation to the relevant observability or drain chapter rather than adding an unplanned fix here.

## Verification

The chapter gate is a reproducible operator checklist with local fixture evidence and, when authorized,
one bounded production smoke. This record is explicitly a **partial T0/T1/T2 plus downstream contract
smoke**; it is not a complete T4 smoke. No product code or unplanned operational capability was added.

**Refactor gate:** no refactor was needed — this chapter changed one operator document only; there is
no production method, class, branch, or test fixture implementation to refactor.

## Out of scope

Full crawling, HTML extraction, link following, Playwright, screenshots, evidence storage, voting, moderation, promotion, scheduled emit, and automatic retry policy.
