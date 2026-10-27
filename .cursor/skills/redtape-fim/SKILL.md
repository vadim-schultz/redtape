---
name: redtape-fim
description: >-
  FIM Portal REST API for discovery enrich (steckbrief/stammtext). Use when
  implementing chapter 17 FIM enrich client or mapping FIM responses to
  discovery entities, claims, and catalogue raw_payload.
---

# FIM Portal (discovery enrich)

Staging contract:
[`.plans/discovery-layer/02-staging-model-and-api.md`](../../../.plans/discovery-layer/02-staging-model-and-api.md)
(§8 CoS skills, `discovery_source=fim`, enrich via chapter 17 — not catalogue ingest).

**Enrich implementation:** [chapter 17](../../../.plans/discovery-layer/chapters/17-fim-leika-enrich.md)
(`discovery_ingest` FIM client + enrich subcommand; `FIM_PORTAL_BASE_URL`).

## When to use

- Chief-of-staff or chapter-implementer work on **FIM Portal enrich** (`discovery_source=fim`).
- You need steckbrief / stammtext routes, OpenAPI entry points, deprecation rules, or how FIM JSON maps to **`discovery_entity` / `discovery_claim`** and `catalogue_service.raw_payload`.
- You are **not** ingesting GovData OZG or PVOG catalogue rows (see `redtape-govdata` / `redtape-pvog`) or documenting LeiKa-only `source=leika` stammtext conventions (see `redtape-leika`).

**Ingest vs enrich:** `fim` is **enrich only** — call FIM after catalogue rows exist (often triggered by `enrich_metadata` tasks from fanout when `fim_id` or steckbrief keys are present).

Prefer **`/api/v1/leistung-steckbriefe`** and **`/api/v1/leistung-stammtexte`**. Do **not** add new integrations on legacy aggregate routes **`/services`** or **`/xzufi-services`** (removed from current OpenAPI; migrate per route migration news).

## Authoritative documentation

Endpoint tables, env defaults, and cross-source `raw_payload` keys live in the checked-in canon — do not duplicate full path registries here:

[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § FIM Portal.

| Resource | URL |
| --- | --- |
| FIM portal data sources | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |
| Swagger UI | https://fimportal.de/docs |
| Kataloge (bulk CSV/XZuFi) | https://fimportal.de/kataloge |
| Steckbrief/stammtext route migration | https://fimportal.de/news/692ea5550be8335ab000a400 |

OpenAPI descriptor: `GET {FIM_PORTAL_BASE_URL}/openapi.json` (see canon).

## API base URLs

| Use | Base / entry |
| --- | --- |
| **FIM Portal REST (chapter 17 default)** | `https://fimportal.de` — override with `FIM_PORTAL_BASE_URL` (no trailing slash before `/api/...`) |
| Swagger UI | `{FIM_PORTAL_BASE_URL}/docs` |
| OpenAPI JSON | `{FIM_PORTAL_BASE_URL}/openapi.json` |
| Bulk exports (out of scope for HTTP enrich client) | `{FIM_PORTAL_BASE_URL}/kataloge` |

**Candidate enrich endpoints** (confirm paths against OpenAPI before production calls):

| Use | Method | Path |
| --- | --- | --- |
| Steckbrief search | `GET` | `/api/v1/leistung-steckbriefe` |
| Steckbrief by key | `GET` | `/api/v1/leistung-steckbriefe/{leistungsschluessel}` |
| Stammtext search | `GET` | `/api/v1/leistung-stammtexte` |
| Stammtext by ids | `GET` | `/api/v1/leistung-stammtexte/{redaktion_id}/{leistung_id}/{source}` |
| Organisational units (compat) | `GET` | `/api/v0/organizational-unit` |
| Org unit XZuFi (compat) | `GET` | `/api/v0/organizational-unit/{redaktion_id}/{organisationseinheit_id}/xzufi` |
| Onlinedienst XZuFi (compat) | `GET` | `/api/v0/online-service/{redaktion_id}/{onlinedienst_id}/xzufi` |

Use **`/api/v1/...`** for new code; `/api/v0/...` remains for compatibility only.

**Stammtext `{source}`** query path segment includes `leika`, `landesredaktion`, and `pvog` (OpenAPI enum). LeiKa-specific mapping lives in `redtape-leika`.

## Authentication

Public **`GET`** for read endpoints used in enrich. No API key on the default enrich path.

Uploads, `/tools/*`, and write operations are out of scope for discovery enrich.

Machine API entity/claim upserts require `DISCOVERY_API_KEY` and `DISCOVERY_API_URL` (chapter 17).

## Deprecations

- Do **not** document or implement new callers on **`/services`** or **`/xzufi-services`** aggregate routes.
- Follow [steckbrief/stammtext migration](https://fimportal.de/news/692ea5550be8335ab000a400) and the current `openapi.json` operation list.

## Rate limits

No published hard quota on public read endpoints. Use modest concurrency, exponential backoff on **`429`** and **`503`**, and honor **`Retry-After`** when present. **CI and unit tests use fixtures only** — no live FIM Portal network in `./ci.sh`.

## Corporate network (manual FIM / Swagger)

On R&S laptops, export `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` before `curl`, browser Swagger, or manual enrich runs. See
[corporate-build-env.md](../chief-of-staff/corporate-build-env.md) and canon § Corporate network.

**httpx (`apps/discovery-ingest`):** use default `trust_env=True` so proxy env vars apply in manual runs.

## Environment variables

| Variable | Default | Role |
| --- | --- | --- |
| `FIM_PORTAL_BASE_URL` | `https://fimportal.de` | FIM REST prefix for chapter 17 client |
| `DISCOVERY_API_URL` | (required for enrich) | Redtape discovery machine API base |
| `DISCOVERY_API_KEY` | (required for enrich) | `X-API-Key` for entity/claim upserts |

## Real steckbrief shape (probed 2026-10-26)

`fim probe` read ten live steckbriefe (five GovData `leika_key`, five PVOG `leikakeys[0]`); all answered 200 with
`leistungsschluessel`. The real top-level keys are `redaktion_id`, `leistung_id`, `title`, `title_en`,
`leistungsbezeichnung`, `leistungsbezeichnung_en`, `leistungsbezeichnung_2`, `leistungsbezeichnung_2_en`,
`rechtsgrundlagen`, `rechtsgrundlagen_en`, `freigabe_status`, `erstellt_datum_zeit`, `geaendert_datum_zeit`,
`leistungsadressat`, `leistungsschluessel`, `typisierung`, `leistungstyp`, `sdg_informationsbereiche`,
`klassifizierung`, `leistung_stammtexte`, `prozessklasse`, `ozg`, `replacements`. There is **no `kurztext`** and no
document, form or evidence field. `leistung_stammtexte` lists `{redaktion_id, id, title, leistungsschluessel}`
references to text modules (a separate fetch, not built).

**Known mismatch:** the enrich helpers still read `titel` and `kurztext`, which the real response does not have, so
entities get no label and no `metadata` claim. The fragment below is an illustration from the early fixtures, not the
real shape. Run `python -m discovery_ingest fim probe --keys <14-digit keys>` to see live keys.

## Example steckbrief fragment (truncated, illustrative)

```json
{
  "leistungsschluessel": "LB-EXAMPLE-STECK",
  "titel": "Beispiel-Leistung",
  "kurztext": "Kurzbeschreibung …",
  "redaktion_id": "RED-EXAMPLE",
  "leistung_id": "LB-EXAMPLE-001"
}
```

Store the **full FIM JSON** in enrich snapshots (`raw_payload` on related catalogue rows or entity metadata per chapter 17).

## `external_id`

Stable id for enrich-side rows tied to FIM (align with canon § `fim` / `leika` enrich snapshots):

`fim:{leistungsschluessel}`

When enrich is keyed by stammtext path segments instead of steckbrief key, use:

`fim:{redaktion_id}:{leistung_id}:{source}`

| Segment | Source field | Notes |
| --- | --- | --- |
| `leistungsschluessel` | Steckbrief primary key | Preferred when fanout provides `fim_id` / steckbrief key |
| `redaktion_id`, `leistung_id`, `source` | Stammtext path segments | `source` is OpenAPI enum (`pvog`, `landesredaktion`, …); use `redtape-leika` when `source=leika` |

## Mapping

FIM enrich **does not** call `POST /catalogue/batch`. It reads existing `catalogue_service` rows (for example `source=govdata` or `pvog`), fetches FIM metadata, then upserts **`discovery_entity`** and **`discovery_claim`** via the machine API (chapter 17).

| FIM response field | Discovery target | Notes |
| --- | --- | --- |
| (constant) | enrich provenance | Treat API host as FIM; `discovery_source` for enrich snapshots is `fim` |
| see § `external_id` | entity / claim stable keys | max 200 chars where stored as string ids |
| `titel` / title fields | claim or entity display metadata | map to i18n shape expected by machine API |
| `kurztext`, long text fields | claim `metadata` / description stubs | chapter 17 maps to suggestion-oriented stubs |
| entire steckbrief or stammtext object | enrich `raw_payload` | include keys below for fanout and audit |

**`raw_payload` keys for fanout** (canon § Cross-source identifiers — copy source-native names):

| Field | Fanout use |
| --- | --- |
| `leistungsschluessel` | Steckbrief primary key; alias for `fim_id` when present on ingest rows |
| `redaktion_id` | FIM redaktion segment; LeiKa enrich |
| `leistung_id` | FIM leistung segment; LeiKa enrich |
| `source` | Stammtext source enum on stammtext routes |
| `organisationseinheit_id` | Org unit enrich |

**Inputs from catalogue ingest (not from FIM):** when GovData/PVOG rows already carry `fim_id`, `leika_key`, or parsed `redaktion_id` / `leistung_id`, use those to choose steckbrief vs stammtext URLs before calling FIM.

## Verification (skill + URLs)

After editing this skill, run the discovery skill checker (validates headings, staging link, canon link, and at least three `https://` URLs):

```bash
./scripts/check_discovery_skills.sh fim
```
