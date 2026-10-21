# Government data sources (discovery ingest)

Canonical URLs and roles for the discovery layer staging ingest loop. Staging contract:
[`.plans/discovery-layer/02-staging-model-and-api.md`](../../.plans/discovery-layer/02-staging-model-and-api.md) §3
(`catalogue_service`, `discovery_source` enum).

## Ingest vs enrich

| `discovery_source` | Loop role | Primary access |
| --- | --- | --- |
| `govdata` | **Catalogue ingest** (chapter 12) | GovData OZG federal dataset (PVOG-derived metadata) |
| `pvog` | **Catalogue ingest** (chapter 13) | PVOG Suchdienst REST API |
| `fim` | **Enrich** (chapter 17) | FIM Portal REST API |
| `leika` | **Enrich** (chapter 17) | FIM Portal (`source=leika`) + bulk downloads from Kataloge |
| `manual` | Ops / tests | N/A |

## Out of scope (v1)

| Source | Reason |
| --- | --- |
| BVA OZG/SDG overview | Not renewed; see [FIM portal data sources](https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/) |
| Land/kommunal OZG dumps (e.g. Schleswig-Holstein `ozg-dienstenutzung`) | Jurisdiction-specific; future ingest |
| [servicesuche.bund.de](https://servicesuche.bund.de) | Human search UI, not machine ingest |
| OpenPLZ | Locations strand, not discovery catalogue |

**XZuFi** is a document format (bulk exports on FIM Kataloge), not a separate `discovery_source`.

---

## Corporate network (manual runs and research)

On R&S developer machines, outbound HTTPS to GovData, FITKO (PVOG/FIM), and `fimportal.de` typically
requires the **corporate HTTP proxy**. CI and unit tests **must not** depend on that network (fixtures only,
D12).

**Reference (do not commit secrets):** [.cursor/skills/chief-of-staff/corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md) — export before chapter **7a** Swagger/CKAN research, manual `discovery_ingest` runs, or debugging ingest clients on a laptop.

| Variable | Role |
| --- | --- |
| `HTTP_PROXY` / `HTTPS_PROXY` | Forward GovData CKAN, PVOG, FIM Portal traffic |
| `NO_PROXY` | Keep `localhost` / `127.0.0.1` direct for local Litestar (`DISCOVERY_API_URL`) |

**httpx (`apps/discovery-ingest`):** use default `trust_env=True` so proxy env vars apply in manual runs; do not hard-disable proxy in clients.

**Example (after exporting proxy vars from corporate-build-env):**

```bash
curl -fsS 'https://ckan.govdata.de/api/3/action/status_show' | head -c 200
```

If connections reset with no proxy, or time out with proxy misconfigured, fix env before re-running research tasks in [chapter 7a](../../.plans/discovery-layer/chapters/07a-government-data-sources-canon.md).

---

## GovData

| Purpose | URL |
| --- | --- |
| Portal | https://data.gov.de/ |
| CKAN Action API | https://ckan.govdata.de/api/3/action/ |
| CKAN mirror | https://www.govdata.de/ckan/api/3/action/ |
| CKAN API guide | https://docs.ckan.org/en/latest/api/ |
| **Primary dataset** | https://www.govdata.de/suche/daten/ozg-leistungen-und-zugehorige-onlinedienste |
| OZG tag search | https://www.govdata.de/suche?tags=ozg |

**Resolved via `package_show` (2026-10-15):** `id=ozg-leistungen-und-zugehorige-onlinedienste`

| CKAN field | Value |
| --- | --- |
| Package name / id | `ozg-leistungen-und-zugehorige-onlinedienste` |
| Package UUID | `7e066f02-06e4-4c16-91aa-8a5e700dcdf2` |
| Title | OZG-Leistungen und zugehörige Onlinedienste |

| Resource name | Resource UUID | Ingest use |
| --- | --- | --- |
| **Leistungen** | `4b4fc7a2-8776-484d-834f-185590b181db` | **Primary JSON feed** — paginated `GET` (see URL below) |
| **REST-API** | `cacb63f7-d635-40a5-9c5b-4ecc4a074f44` | OpenAPI descriptor (`dashboard-digitale-verwaltung.json`) |
| Gebietskörperschaften | `28a0e72e-063f-41e4-9416-5e1ea3d719a4` | ARS lookup helper |
| Leistungen pro Kommune | `ba66f608-02a9-41e2-86a4-460bce615153` | Example commune slice (Wiesbaden) |
| Dashboard Digitale Verwaltung | `cfbc0986-105a-414b-a6d5-cd9c78d03d28` | Human HTML dashboard (not ingest) |

**Leistungen JSON entry points:**

| Feed | URL | Ingest use |
| --- | --- | --- |
| National (all ARS) | `https://api.ozg-umsetzung.de/api/public/v1/dash/open-pvog?order=asc&page=0&size=100` | CKAN resource default; ~1.2M rows |
| **Bund (scheduled GHA default)** | `https://api.ozg-umsetzung.de/api/public/v1/dash/open-pvog/000000000000?order=asc&page=0&size=100&includeAbove=false&includeBelow=false` | Federal scope only (`GOVDATA_OPEN_PVOG_ARS`) |

OpenAPI: `GET /public/v1/dash/open-pvog/{ars}` on the dashboard Data Hub API.

**REST-API OpenAPI (dashboard):**

`https://api.ozg-umsetzung.de/api/v3/api-docs/dashboard-digitale-verwaltung`

**Authentication:** public read; no API key for CKAN Action API.

**Rate limits:** be polite; batch downloads; CI uses fixtures only.

**Environment (optional):**

| Variable | Default |
| --- | --- |
| `GOVDATA_CKAN_BASE_URL` | `https://ckan.govdata.de/api/3/action` |
| `GOVDATA_PACKAGE_ID` | `ozg-leistungen-und-zugehorige-onlinedienste` |
| `GOVDATA_OPEN_PVOG_ARS` | `000000000000` (Bund); rewrites CKAN Leistungen URL to `open-pvog/{ars}` |

**Note:** OZG dataset content is based on PVOG; catalogue rows may include cross-refs usable for enrich fanout.

---

## PVOG

| Purpose | URL |
| --- | --- |
| Product portal | https://pvog.fitko.de/ |
| **API base (default)** | `https://pvog.fitko.net/suchdienst/api` |
| Suchdienst API overview | https://pvog.fitko.de/api/suchdienst/portalverbund-suchdienst-rest-api/ |
| Suchdienst API index | https://produktportal.pvog.fitko.de/api/suchdienst/ |
| Swagger UI | https://pvog.fitko.net/suchdienst/api/swagger-ui/index.html |
| OpenAPI 3 | https://pvog.fitko.net/suchdienst/api/v3/api-docs |
| Deprecations | https://pvog.fitko.de/api/deprecations/ |
| Domain migration | https://pvog.fitko.de/blog/Umzug_pvog_fitko_net/ |
| Bereitstelldienst (bulk) | `https://pvog.fitko.net/bereitstelldienst/api` |
| Client ID | PVOG portal → Ressourcen → Client ID |

**Authentication:**

- **Suchdienst:** public search endpoints (chapter 13 default).
- **Bereitstelldienst:** registered Client ID; optional bulk path, not required for v1 loop.

**Deprecations:** avoid endpoints listed on the [deprecations page](https://pvog.fitko.de/api/deprecations/) (Suchdienst and Bereitstelldienst tables). Honor response header `X-PVOG-DEPRECATED: true`.

**Excluded Suchdienst paths (deprecated, do not use for new ingest):**

| Path | Notes |
| --- | --- |
| `/v2/locations/suggestions` | Deprecated Mai 2026 |
| `/v2/locations` | Deprecated Mai 2026 |
| `/v2/organisationunits/jzufi` | Deprecated Mai 2026 |
| `/v3/relations/{ars}/jzufi` | Deprecated Mai 2026 |
| `/v3/servicedescriptions/jzufi` | Deprecated Mai 2026 |
| `/v5/servicedescriptions/{ars}/detail` | Deprecated Mai 2026 |

**Bereitstelldienst:** `/v2/verwaltungsobjekte` is deprecated — not used in v1 loop.

**Environment:**

| Variable | Default |
| --- | --- |
| `PVOG_API_BASE_URL` | `https://pvog.fitko.net/suchdienst/api` |

### Candidate Suchdienst endpoints (chapter 13)

Derived from OpenAPI (`v3/api-docs`, 2026-10-15). Prefer current **Leistungen** (`servicedescriptions`) and **Onlinedienste** families; use beta paths only when stable vNext is unavailable.

**Onlinedienste (list / detail / orgs):**

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/v1beta2/onlineservices` | List onlinedienste in ARS scope (`ars`, optional `leikaIds`, `nextPageToken`) |
| `GET` | `/v1beta2/onlineservices/{odId}/organisations` | Orgs responsible for an onlinedienst |
| `GET` | `/v2/onlineservices/detail` | Onlinedienst detail (`q` = onlinedienst id) |
| `GET` | `/v3beta1/onlineservices/{odId}/detail` | Beta detail variant |

**Leistungen / servicedescriptions (list / detail / lookup):**

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/v7/servicedescriptions/{ars}` | Leistungen for ARS (current major list; **requires** search criteria — see below) |
| `GET` | `/v6/servicedescriptions/{lbid}/detail` | Leistung detail by `lbId` |
| `GET` | `/v3/servicedescriptions/leikaid` | Lookup by LeiKa id |
| `GET` | `/v4beta1/servicedescriptions/leikaid` | Beta LeiKa lookup |
| `GET` | `/v2/servicedescriptions/leikahierarchy` | LeiKa hierarchy |
| `GET` | `/v1/servicedescriptions/suggestions/{ars}` | Suggestions for ARS |
| `GET` | `/v8beta1/servicedescriptions` | Beta list (evaluate before production ingest) |

**Supporting lookups (not deprecated at time of research):**

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/v3/locations` | ARS / location search |
| `GET` | `/v3/locations/suggestions` | Location suggestions |
| `GET` | `/v5/organisationunits/detail` | Organisation unit detail |

**Pagination:** beta onlinedienste use `nextPageToken`; v7 Leistungen use `serviceDescriptions` page index (see **Federal ingest**); mirror shapes in `tests/fixtures/pvog/` (chapter 13).

### Federal ingest (`pvog run`, v7)

Scheduled **Platform maintenance** discovery runs call `python -m discovery_ingest pvog run` with federal ARS
`000000000000` ([`FEDERAL_ARS`](../../apps/discovery-ingest/discovery_ingest/pvog/client.py)). PVOG v7 rejects
parameterless list requests (`400`, API code **1901** — search must include `q`, LeiKa ids, or Lebenslagen).

| Phase | Query | Role |
| --- | --- | --- |
| Bootstrap | `personalMatters=Geburt`, `facades=true`, `size=100` | Discover `facades.personalMatters` tree ([`BOOTSTRAP_PERSONAL_MATTER`](../../apps/discovery-ingest/discovery_ingest/pvog/client.py)) |
| Code list | DFS on bootstrap tree | Collect **leaf** `code` only (nodes without `children`); `sorted(set(codes))` for deterministic order |
| Search | Per leaf code: `personalMatters={code}`, `facades=false`, `page=0…` | Paginate until `serviceDescriptions.last` is true |
| Dedupe | Within one run | Skip rows whose lb `id` was already yielded from another `personalMatters` code |

**v7 response shape:** rows live in `serviceDescriptions.content`; advance `page` while `last` is false. Do not rely on
legacy top-level `content` / `next` on bare `GET …/v7/servicedescriptions/{ars}`.

**HTTP budget:** CLI `--max-pages` counts **every** Suchdienst GET (bootstrap plus all code pages). GHA uses
`--max-pages 50` until a follow-up raises the cap ([platform-maintenance workflow](../../.github/workflows/platform-maintenance.yml)).

**Alternatives (not the scheduled path):** `q` text search or LeiKa id parameters satisfy v7 without a Lebenslagen walk;
supplement crawls are documented as open seams in [`.plans/pvog-v7-ingest/gaps-and-decisions.md`](../../.plans/pvog-v7-ingest/gaps-and-decisions.md).

---

## FIM Portal

| Purpose | URL |
| --- | --- |
| Data-source matrix | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |
| FIM documentation hub | https://docs.fitko.de/fim/docs/ |
| **REST Swagger** | https://fimportal.de/docs |
| OpenAPI JSON | https://fimportal.de/openapi.json |
| Kataloge (bulk CSV/XZuFi) | https://fimportal.de/kataloge |
| Route migration (steckbrief/stammtext) | https://fimportal.de/news/692ea5550be8335ab000a400 |

**Authentication:** public `GET` for read endpoints used in enrich; no API key. Uploads and `/tools/*` are out of scope.

**Rate limits:** retry on `429` / `503` with backoff (document in `redtape-fim` skill).

**Environment:**

| Variable | Default |
| --- | --- |
| `FIM_PORTAL_BASE_URL` | `https://fimportal.de` |

**Prefer** routes under `/api/v1/leistung-steckbriefe` and `/api/v1/leistung-stammtexte`. Do **not** build new integrations on legacy aggregate routes **`/services`** or **`/xzufi-services`** (removed from current OpenAPI; use steckbrief / stammtext families per [route migration](https://fimportal.de/news/692ea5550be8335ab000a400)).

### Candidate enrich endpoints (chapter 17)

From `openapi.json` (2026-10-15). Use **`/api/v1/...`** for new code; `/api/v0/...` remains for compatibility.

| Use | Method | Path |
| --- | --- | --- |
| Steckbrief search | `GET` | `/api/v1/leistung-steckbriefe` |
| Steckbrief by key | `GET` | `/api/v1/leistung-steckbriefe/{leistungsschluessel}` |
| Stammtext search | `GET` | `/api/v1/leistung-stammtexte` |
| Stammtext by ids | `GET` | `/api/v1/leistung-stammtexte/{redaktion_id}/{leistung_id}/{source}` |
| Organisational units | `GET` | `/api/v0/organizational-unit` |
| Org unit XZuFi | `GET` | `/api/v0/organizational-unit/{redaktion_id}/{organisationseinheit_id}/xzufi` |
| Onlinedienst XZuFi | `GET` | `/api/v0/online-service/{redaktion_id}/{onlinedienst_id}/xzufi` |

**`source` query values** for stammtext include `leika`, `landesredaktion`, and `pvog` (see OpenAPI enum on `{source}`).

---

## LeiKa (logical source)

LeiKa has **no separate HTTP host**. Use FIM Portal and Kataloge.

| Purpose | URL |
| --- | --- |
| Bulk LeiKa-plus / Alle Leistungen | https://fimportal.de/kataloge (XZuFi 2.2.0, CSV) |
| API Stammtext | FIM `/api/v1/leistung-stammtexte/.../{source}` with `source=leika` |
| Secondary ids | PVOG Suchdienst `/v3/servicedescriptions/leikaid` when OZG JSON already carries LeiKa keys |

**`external_id` convention (staging):** `leika:{redaktionId}:{leistungId}` (align with FIM path segments; document exact JSON fields in `redtape-leika` skill).

See also [FIM §](#fim-portal) and chapter 10 vs 11 skill boundary: FIM skill = portal API surface; LeiKa skill = LeiKa identifiers and `source=leika` mapping.

---

## Cross-source identifiers (`raw_payload`)

Keys below are used in [catalogue task fanout](../../.plans/discovery-layer/chapters/14-catalogue-task-fanout.md) (for example enqueue `enrich_metadata` when `fim_id` is present). Ingest mappers should copy **source-native field names** into `catalogue_service.raw_payload` (plus normalized aliases where noted).

### `govdata` (OZG Leistungen JSON)

| Field | Notes |
| --- | --- |
| `leika_key` | LeiKa service key (14 digits); primary `external_id` segment |
| `leika_name` | Display title in current OpenPvogDto exports |
| `leika_bezeichnung` | LeiKa description / fallback title |
| `ozgid` | OZG grouping id (numeric; not unique per row — prefer `leika_key` for `external_id`) |
| `ozg_bezeichnung` | OZG service group label |
| `url` | Portal / service URL → `fetch_url` tasks |
| `ars` | Official regional key (Bund = `000000000000`) |
| `online_status` | Availability signal (`ok`, etc.) |

**Fanout alias:** set `leistung_id` from `leika_key` (or parse LeiKa segments) and `redaktion_id` when present in row or derived from URL; set `fim_id` when FIM steckbrief key is known from export metadata.

### `pvog` (Suchdienst responses)

| Field | Notes |
| --- | --- |
| `id` | Leistung id in v7 list rows (lb id); onlinedienst id in relation payloads |
| `lbId` | Leistung id in PVOG relation payloads |
| `leikakeys` / `leikaIds` | LeiKa keys on v7 rows or beta onlinedienste list |
| `ars` | Regional scope on relations / list queries |
| `onlineServiceLinks` / `sourcePortals` | Link objects with `uri` → ingest `portal_url` |
| `relations` | Nested links between onlinedienst and Leistung |

**`external_id` (ingest):** `pvog:leika:{key}` when `leikakeys[0]` or `leikaIds[0]` is present; else `pvog:lb:{id}` from row `id` or `lbId`.

**Fanout:** populate `leistung_id` / `redaktion_id` from `lbId` or LeiKa lookup; `portal_url` from `onlineServiceLinks` / `sourcePortals` or onlinedienst `links[].uri`.

### `fim` / `leika` (enrich snapshots)

| Field | Notes |
| --- | --- |
| `leistungsschluessel` | Steckbrief primary key |
| `redaktion_id` | FIM redaktion segment |
| `leistung_id` | FIM leistung segment |
| `source` | Stammtext source (`leika`, `pvog`, `landesredaktion`) |
| `organisationseinheit_id` | Org unit enrich |

Store the full source row in `catalogue_service.raw_payload` for audit.

| Key / concept | Typical source | Fanout use |
| --- | --- | --- |
| `fim_id` | GovData OZG row / FIM steckbrief key | Enrich via FIM when present |
| `redaktion_id`, `leistung_id` | OZG / PVOG / FIM | LeiKa enrich |
| PVOG `id` / `lbId` / LeiKa keys | OZG JSON, PVOG API | Dedup and `external_id` for `pvog` source (`pvog:leika:…` or `pvog:lb:…`) |
| `portal_url` / `url` | All ingest paths | `fetch_url` tasks |

---

## Related plans

| Chapter | Plan |
| --- | --- |
| 7a | [07a-government-data-sources-canon.md](../../.plans/discovery-layer/chapters/07a-government-data-sources-canon.md) |
| Skills 8–11 | [chapters/](../../.plans/discovery-layer/chapters/) |
| GovData ingest | [12-govdata-ozg-ingest.md](../../.plans/discovery-layer/chapters/12-govdata-ozg-ingest.md) |
| PVOG ingest | [13-pvog-ingest-cli.md](../../.plans/discovery-layer/chapters/13-pvog-ingest-cli.md) |
| Enrich | [17-fim-leika-enrich.md](../../.plans/discovery-layer/chapters/17-fim-leika-enrich.md) |
