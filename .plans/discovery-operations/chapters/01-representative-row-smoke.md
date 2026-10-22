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

**Repo:** `redtape` · **Branch:** `feat/discovery-operations-row-smoke` · **Status:** planned

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

The chapter gate is a reproducible operator checklist with local fixture evidence and, when authorized, one bounded production smoke. The final record must distinguish a complete T4 smoke from a partial T0/T1/T2 smoke.

## Out of scope

Full crawling, HTML extraction, link following, Playwright, screenshots, evidence storage, voting, moderation, promotion, scheduled emit, and automatic retry policy.
