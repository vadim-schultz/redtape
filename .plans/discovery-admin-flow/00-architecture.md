# Discovery admin flow consolidation - architecture

This work package makes the pipeline flow page the only discovery admin view. It moves the data of the removed views into the flow response, and it reduces the language menu to flags.

## Purpose

The discovery admin has five list views, two drill-down pages and one flow page. The flow page shows the stages, the edges, the budget allotments and the unused headroom. The other views repeat counts that the flow can carry. The top-level menu shows five discovery links. The language menu shows a flag, a code and a machine-translation note for each locale.

This work package does the following:

- Adds the counts of the removed views to the flow response.
- Shows those counts on the flow page.
- Removes the other admin views, their routes, their endpoints and the code that only they use.
- Shows one discovery menu link, to the flow page.
- Shows language flags only. The menu shows no code and no machine-translation note.

Out of scope:

- The machine router under `/api/v1/discovery/machine`, the discovery ingest worker and the data model.
- The public Browse documents page at `/documents` and its API.
- New filters, sorting, charts or paging on the flow page.
- Row-level browsing, unless open question O1 changes its default.
- Any change to admin authorization. The server guard stays the security boundary.

### Current admin surface

| Surface | Route | Endpoints | Disposition |
| --- | --- | --- | --- |
| Flow | `/admin/discovery/flow` | `GET /api/v1/discovery/admin/flow` | Keep. Extended by C1 and C3. |
| Catalogue | `/admin/discovery/catalogue` | `GET /api/v1/discovery/admin/catalogue` | Remove. Summary chips move to the flow. Rows go (O1). |
| Coverage | `/admin/discovery/coverage` | `GET /api/v1/discovery/admin/coverage`, `GET /api/v1/discovery/admin/budgets/`, `GET /api/v1/admin/translations/coverage` | Remove. Figures move to the flow. |
| Tasks | `/admin/discovery/tasks` | `GET /api/v1/discovery/admin/tasks` | Remove. Per-stage counts and recent failures move to the flow. The tasks endpoint is also the admin probe, so C4 moves the probe first. |
| Documents | `/admin/discovery/documents` | `GET /api/v1/discovery/admin/candidates` | Remove. Candidate counts move to the flow. |
| Document detail | `/admin/discovery/documents/:id` | `GET /api/v1/discovery/admin/candidates/{id}`, `.../edges`, `.../emit-preview`, `.../artifacts` | Remove (O1, O2). |
| Pipeline detail | `/admin/discovery/pipeline/:id` | `GET /api/v1/discovery/admin/catalogue/{id}/pipeline`, `.../emit-preview`, `.../artifacts` | Remove (O1, O2). |
| Discovery menu | `DiscoveryAdminMenuLinks` | none | One link: Flow. |
| Language menu | `LanguageMenuRow` | none | Flags only. |

The admin router has no write endpoint. The admin frontend sends only `GET` requests. Removing these views removes no write path. Emit writes stay on the machine router.

### Flow response contract

The flow response keeps every existing field. C1 and C3 add the fields below. C4 mirrors them in the frontend type.

| Field | Content | Source today | Added in |
| --- | --- | --- | --- |
| `catalogue` | `total`, `by_source`, `by_pipeline_stage` | Catalogue summary chips | C1 |
| `candidates` | `total`, `staged`, `emitted`, `mentions`, `emit_ready` | Coverage candidate counts and `emit_ready_count` | C1 |
| `sources` | Count per discovery source | Coverage `by_source` | C1 |
| `tasks` | `total`, `pending`, `claimed`, `completed`, `failed` | Coverage `task_counts` | C1 |
| `llm_outcomes` | `extracted`, `no_documents`, `login_wall`, `no_content` | Coverage `llm_outcomes` | C1 |
| `artifacts` | `by_kind`, `total_bytes`, `bytes_cap` | Coverage `artifacts` | C1 |
| `fetch_attempts_total`, `stale_claims`, `stale_runs` | Counters | Coverage | C1 |
| `failures_by_source` | Count per source | Coverage | C1 |
| `last_successful_run` | Newest successful run, or `null` | Coverage | C1 |
| `allotments[].period`, `allotments[].exhausted` | Current period and exhausted flag | Budget snapshot | C1 |
| `translation` | `denominator`, `snapshot_denominator`, `locales` | Translation admin coverage | C3 |
| `stages[].tasks` | Task counts of the stage's kinds. `null` for queue stages. | Coverage `task_counts_by_kind` | C3 |
| `stages[].recent_failures` | At most 20 failed tasks, newest first | Tasks endpoint | C3 |

## Invariants

| ID | Invariant | Check |
| --- | --- | --- |
| I1 | `GET /api/v1/discovery/admin/flow` is the only admin read endpoint that remains. It keeps `DISCOVERY_ADMIN_GUARDS`. | C6 adds a test that answers `404` for each removed route. The flow guard tests stay green. |
| I2 | The flow response keeps every existing field, with its name and type. | `tests/test_discovery_flow_route.py` stays green. Its assertions change only where they compare a whole response. |
| I3 | The machine routes under `/api/v1/discovery/machine` and the public `/documents` API keep their responses. | Their test files pass without edits to their assertions. |
| I4 | A flow read writes nothing. | C1 tests that the row counts of the read tables do not change after a flow read. |
| I5 | No Alembic migration is added. | The local gate runs `scripts/check_migrations.sh`. |
| I6 | The admin menu probe calls the flow route. Discovery links show only when the probe succeeds. | C4 probe tests. C5 menu tests. |
| I7 | Each language flag button keeps its native language name as accessible name. The menu shows no code and no machine-translation note. | C2 tests. |
| I8 | Each chapter passes the local gate on its chapter branch before the chief of staff integrates it. | The run ledger records the gate for each chapter. |

## Decided

The decisions D1 to D12 hold for the whole work package. They live in [gaps-and-decisions.md](gaps-and-decisions.md) with their reasons.

## Open

Three questions remain open. Each has a default in [gaps-and-decisions.md](gaps-and-decisions.md):

- O1: whether the flow keeps row-level detail. Default: no. The flow shows totals and at most 20 recent failed tasks per stage.
- O2: whether the admin emit previews survive. Default: no. The machine emit route is unchanged.
- O3: whether the one-minute flow refresh still fits the added queries. Default: keep the refresh. C1 records the query count and the elapsed time of one read.
