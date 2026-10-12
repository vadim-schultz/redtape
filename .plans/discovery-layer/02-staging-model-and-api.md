---
name: Discovery layer — Staging model and API
overview: "Implementer contract: Postgres staging tables, pipeline stages T0–T4, machine and admin HTTP routes, ingest package layout, emit mapping to suggestions."
isProject: false
---

# Discovery layer — Staging model and API

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md)

---

## 1. Settings

Add to [apps/api/app/config.py](../../apps/api/app/config.py) (mirror `auth_enabled`):

| Field | Purpose |
| --- | --- |
| `discovery_admin_emails` | Comma-separated allowlist; parsed to `frozenset[str]` (lowercase) |
| `discovery_enabled` | `True` when allowlist non-empty **or** explicit opt-in flag for machine routes in dev |

Machine routes return 503 when discovery is disabled. Admin routes require `auth_enabled` and discovery allowlist.

---

## 2. Enums (Postgres native)

| Enum | Values |
| --- | --- |
| `discovery_source` | `govdata`, `pvog`, `fim`, `leika`, `manual` |
| `discovery_task_status` | `pending`, `claimed`, `completed`, `failed` |
| `discovery_task_kind` | `fetch_url`, `enrich_metadata` |
| `discovery_claim_kind` | `new_document`, `new_requirement`, `metadata` |
| `discovery_event_type` | `catalogue_upserted`, `task_enqueued`, `task_claimed`, `fetch_logged`, `claim_recorded`, `emit_attempted` |

---

## 3. Tables

### `catalogue_service`

Imported **Leistung** / OZG service row (staging only; D7).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `source` | `discovery_source` | |
| `external_id` | string(200) | Stable id from source API |
| `jurisdiction_id` | FK `jurisdiction.id` | RESTRICT |
| `title_i18n` | JSONB | At least one locale |
| `description_i18n` | JSONB | nullable |
| `portal_url` | string(500) | nullable |
| `raw_payload` | JSONB | Source snapshot for audit |
| `pipeline_stage` | string(2) | `T0`–`T4`, derived (§5) |
| `created_at`, `updated_at` | timestamptz | |

Unique: `(source, external_id)`.

### `discovery_entity`

Resolvable thing (URL, future document anchor).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `catalogue_service_id` | FK `catalogue_service.id` CASCADE | |
| `canonical_url` | string(500) | Normalized like suggestion `normalized_url` |
| `label` | string(500) | nullable display |
| `created_at` | timestamptz | |

Unique: `(catalogue_service_id, canonical_url)`.

### `discovery_task`

Work queue for fetch/enrich (D5 auto-enqueue on catalogue upsert).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `catalogue_service_id` | FK CASCADE | |
| `kind` | `discovery_task_kind` | |
| `target_url` | string(500) | |
| `status` | `discovery_task_status` | default `pending` |
| `priority` | int | lower = sooner; default 100 |
| `claimed_at` | timestamptz | nullable |
| `claimed_by_api_key_id` | FK `api_key.id` SET NULL | nullable |
| `lease_expires_at` | timestamptz | nullable |
| `last_error` | text | nullable |
| `created_at`, `updated_at` | timestamptz | |

Index: `(status, priority, created_at)` for admin queue and claim.

### `discovery_fetch_log`

Append-only fetch attempts (machine writes).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `discovery_task_id` | FK `discovery_task.id` CASCADE | |
| `http_status` | int | nullable if connection error |
| `fetched_at` | timestamptz | |
| `content_type` | string(200) | nullable |
| `byte_length` | int | nullable |
| `error_message` | text | nullable |

### `discovery_claim`

Staging claims before emit (D8: requirement edges may reference unresolved entity ids).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `discovery_entity_id` | FK CASCADE | |
| `kind` | `discovery_claim_kind` | |
| `payload` | JSONB | Shape per kind; validated in service |
| `confidence` | numeric(3,2) | nullable 0–1 |
| `created_at` | timestamptz | |

### `discovery_event`

Lineage audit (chapter 1).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `event_type` | `discovery_event_type` | |
| `catalogue_service_id` | FK SET NULL | nullable |
| `discovery_task_id` | FK SET NULL | nullable |
| `payload` | JSONB | Small context blob |
| `created_at` | timestamptz | |

Index: `(catalogue_service_id, created_at)`.

---

## 4. API layout

Package: `apps/api/app/features/discovery/` — `router.py` (two routers), `machine_controller.py`, `admin_controller.py`, `service.py`, `repository.py`, `dependencies.py`, `pipeline.py` (stage derivation), `emit.py` (chapter 18).

Register in `main.py` only when `discovery_enabled` or always mount with 503 guards (match auth pattern).

### Machine routes (`X-API-Key`, `require_machine`)

Prefix: `/api/v1/discovery/machine`

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/catalogue/batch` | Upsert up to N `catalogue_service` rows; auto-enqueue `fetch_url` task when `portal_url` set |
| `POST` | `/tasks/claim` | Body `{limit?: int}` → assign `pending` tasks to caller key with lease |
| `POST` | `/tasks/{id}/complete` | Mark task completed |
| `POST` | `/tasks/{id}/fail` | Mark failed + `last_error` |
| `POST` | `/tasks/{id}/fetches` | Append `discovery_fetch_log` |
| `POST` | `/entities` | Upsert entity under catalogue row |
| `POST` | `/claims` | Append `discovery_claim` |

### Admin routes (Bearer JWT + email allowlist)

Prefix: `/api/v1/discovery/admin`

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/tasks` | Paginated queue (`status`, `source` filters) |
| `GET` | `/catalogue` | Paginated catalogue index + summary chips payload |
| `GET` | `/catalogue/{id}/pipeline` | Aggregate: service, tasks, fetches, entities, claims, events |
| `GET` | `/catalogue/{id}/emit-preview` | Would-be suggestion payloads (no POST) |
| `GET` | `/coverage` | Metrics for chapter 19 |

Admin guard: `require_discovery_admin` — JWT user email in `discovery_admin_emails`.

---

## 5. Pipeline stages (T0–T4)

Computed on read (not stored except cached `pipeline_stage` on `catalogue_service`, refreshed on write):

| Stage | Meaning |
| --- | --- |
| T0 | Catalogue row ingested, no tasks yet |
| T1 | Task enqueued, not completed |
| T2 | Fetch logged at least once |
| T3 | At least one `discovery_claim` |
| T4 | Emit-ready: all claims for emit have resolvable payloads (chapter 18 rules) |

Implement in `pipeline.py` as pure functions over aggregates; unit-test stage transitions.

---

## 6. Emit mapping (chapter 18)

`DiscoveryEmitService` builds suggestion create bodies:

| `discovery_claim_kind` | Suggestion `kind` | Notes |
| --- | --- | --- |
| `new_document` | `new_document` | Map `payload` → `title_i18n`, `official_url`, optional taxonomy codes |
| `new_requirement` | `new_requirement` | Requires resolved `parent_document_id` / `required_document_id` UUIDs in canonical DB or stub skip (D8) |
| `metadata` | — | Not emitted in v1; admin preview only |

- `source_type`: always `crawler` for machine emit.
- `source_url`: entity `canonical_url`.
- `idempotency_key`: `discovery-emit:{claim_id}` per API key.
- Calls existing `SuggestionService` / HTTP internal — no direct `document` table writes.

---

## 7. `apps/discovery-ingest/`

```
apps/discovery-ingest/
  pyproject.toml
  discovery_ingest/
    config.py          # API base URL, API key from env
    api_client.py      # DiscoveryMachineClient
    govdata/client.py
    pvog/client.py
    fim/client.py
    leika/client.py
    cli.py             # subcommands: govdata, pvog, enrich
  tests/
    fixtures/govdata/*.json
    fixtures/pvog/*.json
```

- **httpx** for gov APIs and redtape discovery API (`trust_env=True` so `HTTP_PROXY` / `HTTPS_PROXY` apply on developer machines; see [government-data-sources.md](../../docs/discovery/government-data-sources.md) § Corporate network).
- CI uses **fixtures only** — no live government network.
- CLIs exit non-zero on API 4xx/5xx.

---

## 8. CoS skill paths (chapters 8–11)

**Canon (chapter 7a):** [docs/discovery/government-data-sources.md](../../docs/discovery/government-data-sources.md) — authoritative URLs, env vars, ingest vs enrich, `raw_payload` keys.

| `discovery_source` | Ingest vs enrich | Skill directory |
| --- | --- | --- |
| `govdata` | Ingest (ch12) | `.cursor/skills/redtape-govdata/` |
| `pvog` | Ingest (ch13) | `.cursor/skills/redtape-pvog/` |
| `fim` | Enrich (ch17) | `.cursor/skills/redtape-fim/` |
| `leika` | Enrich (ch17); FIM host | `.cursor/skills/redtape-leika/` |

Each `SKILL.md`: link to the canon doc (or `## Authoritative documentation` with the same URLs), endpoints, auth, rate limits, example request/response, mapping table to `catalogue_service` + `external_id` convention.

---

## 9. Web admin (`apps/web`)

Feature: `apps/web/src/features/discovery-admin/`

| Route | Page |
| --- | --- |
| `/admin/discovery/tasks` | Chapter 5 |
| `/admin/discovery/catalogue` | Index with chips (chapter 19) |
| `/admin/discovery/pipeline/:id` | Chapter 6–7 |

Not linked from public nav. Layout shell + email gate in chapter 4.
