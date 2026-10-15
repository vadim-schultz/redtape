---
name: Discovery online — Gaps and decisions
overview: "Settled decisions for scheduled discovery, Supabase keep-alive cadence, and ingest idempotency."
isProject: false
---

# Discovery online — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Scheduler = GitHub Actions** (`ubuntu-latest`, `schedule` + `workflow_dispatch`). |
| D2 | **Discovery jobs never use `DATABASE_URL`.** All staging writes via machine API + API key ([discovery-layer D3](../discovery-layer/gaps-and-decisions.md)). |
| D3 | **OpenPLZ path keeps `DATABASE_URL`** in GHA (same as today). |
| D4 | **Supersedes discovery-layer D4** (“no standing GHA discovery”) — this suite adds scheduled discovery intentionally. |
| D5 | **6-day keep-alive cycle** — OpenPLZ on `days % 6 == 0`, discovery on `days % 6 == 3`; daily workflow with no-op on other days. Replaces OpenPLZ Mon+Thu cron. |
| D6 | **Staging-only scheduled runs** — no auto `POST /catalogue/{id}/emit`; emit stays manual ([discovery-layer runbook](../../docs/operations/discovery-layer.md)). |
| D7 | **`DISCOVERY_API_URL` = API host root** — client appends `/api/v1/discovery/machine/...` ([`api_client.py`](../../apps/discovery-ingest/discovery_ingest/api_client.py)). |
| D8 | **Narrow worker in `apps/discovery-ingest`** — not full `apps/crawler` (Playwright/evidence deferred). |
| D9 | **Idempotency = OpenPLZ parity** — chapter 5; scheduled refetch must not stack duplicate `fetch_url` tasks or duplicate claims. |
| D10 | **PR CI uses fixtures only** — no live GovData/PVOG/FIM egress in `api-lint-test` / ingest tests on PRs. |

### Idempotency policy (chapter 5 implements)

| Case | Policy |
| --- | --- |
| `fetch_url` enqueue | Skip new task if one exists for `(catalogue_service_id, kind, target_url)` with status `pending` or `claimed`. Re-enqueue only when `failed` or `portal_url` changed on catalogue row. |
| `enrich_metadata` fanout | Keep existing idempotent `find_pending_task` behavior. |
| `discovery_claim` | Upsert or skip by `(discovery_entity_id, kind, payload_fingerprint)`; `metadata` may update in place. |
| Catalogue / entity race | On `IntegrityError` for unique constraints, re-select by unique key and continue (OpenPLZ pattern). |
| Ingest batch | Collapse duplicate `(source, external_id)` before POST. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| GovData full export runtime | GHA 60m timeout; page caps per run or incremental CKAN |
| Auto-emit on schedule | Product wants moderation queue filled without curl |
| Machine `GET /catalogue/{id}` | LeiKa enrich without admin JWT export file |
| `failed` task retry policy | Operator wants periodic re-fetch of all completed URLs |
| CF cron HTTP drain | Trigger discovery without GHA |
| Full [crawlers](../crawlers/00-architecture.md) suite | Screenshots, evidence, suggestion-mode extractors |

## Deferred (not in this rollout)

- Scheduled emit to suggestions
- `apps/crawler` package and discovery-layer ch.20 as originally scoped
- Evidence attachments (discovery-layer ch.16)
- LLM extract flag (ch.21)
