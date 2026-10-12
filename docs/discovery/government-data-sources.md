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

**Ingest default (chapter 12):** use the dataset **Leistungen** JSON resource (or the dataset **REST-API** resource). Resolve download URLs in manual runs with `package_show` and `resource_show`; record the canonical package id below when confirmed.

| CKAN field | Value (fill during chapter 7a research) |
| --- | --- |
| Package name / id | _TBD via `package_show`_ |
| Resource: Leistungen JSON | _TBD_ |
| Resource: REST-API | _TBD_ |

**Authentication:** public read; no API key for CKAN Action API.

**Rate limits:** be polite; batch downloads; CI uses fixtures only.

**Environment (optional):**

| Variable | Default |
| --- | --- |
| `GOVDATA_CKAN_BASE_URL` | `https://ckan.govdata.de/api/3/action` |
| `GOVDATA_PACKAGE_ID` | OZG package id once resolved |

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
| Deprecations | https://pvog.fitko.de/api/deprecations/ |
| Domain migration | https://pvog.fitko.de/blog/Umzug_pvog_fitko_net/ |
| Bereitstelldienst (bulk) | `https://pvog.fitko.net/bereitstelldienst/api` |
| Client ID | PVOG portal → Ressourcen → Client ID |

**Authentication:**

- **Suchdienst:** public search endpoints (chapter 13 default).
- **Bereitstelldienst:** registered Client ID; optional bulk path, not required for v1 loop.

**Deprecations:** avoid endpoints listed on the deprecations page (e.g. Bereitstelldienst `/v2/verwaltungsobjekte`, several Suchdienst `/v3/.../jzufi` paths). Honor response header `X-PVOG-DEPRECATED: true`.

**Environment:**

| Variable | Default |
| --- | --- |
| `PVOG_API_BASE_URL` | `https://pvog.fitko.net/suchdienst/api` |

**Candidate endpoints (confirm in Swagger during 7a / 13):**

| Area | Example paths (verify version in Swagger) |
| --- | --- |
| Onlinedienste | `/v2/onlineservices/detail` (detail by query params) |
| Leistungen | Suchdienst “Leistungen” family per Swagger |
| Pagination | Follow `next` / page links as returned by API; mirror in `tests/fixtures/pvog/` |

---

## FIM Portal

| Purpose | URL |
| --- | --- |
| Data-source matrix | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |
| FIM documentation hub | https://docs.fitko.de/fim/docs/ |
| **REST Swagger** | https://fimportal.de/docs |
| Kataloge (bulk CSV/XZuFi) | https://fimportal.de/kataloge |
| Route migration (steckbrief/stammtext) | https://fimportal.de/news/692ea5550be8335ab000a400 |

**Authentication:** public `GET` for read endpoints used in enrich; no API key. Uploads and `/tools/*` are out of scope.

**Rate limits:** retry on `429` / `503` with backoff (document in `redtape-fim` skill).

**Environment:**

| Variable | Default |
| --- | --- |
| `FIM_PORTAL_BASE_URL` | `https://fimportal.de` |

**Prefer** routes under `/leistung-steckbrief` and `/leistung-stammtext`. Do not build new integrations on deprecated `/services` or `/xzufi-services`.

**Candidate enrich endpoints (confirm in Swagger during 7a / 17):**

| Use | Swagger area |
| --- | --- |
| Service steckbrief search/get | `leistung-steckbrief` |
| Master text (Stammtext) | `leistung-stammtext` with `source` query (`leika`, `landesredaktion`, `pvog`) |
| Organisational units | `organizational-units` (cursor pagination) |

---

## LeiKa (logical source)

LeiKa has **no separate HTTP host**. Use FIM Portal and Kataloge.

| Purpose | URL |
| --- | --- |
| Bulk LeiKa-plus / Alle Leistungen | https://fimportal.de/kataloge (XZuFi 2.2.0, CSV) |
| API Stammtext | FIM `leistung-stammtext` / `service-texts` with `source=leika` |
| Secondary ids | PVOG Suchdienst when OZG JSON already carries PVOG keys |

**`external_id` convention (staging):** `leika:{redaktionId}:{leistungId}` (align with FIM keys; document exact JSON fields in `redtape-leika` skill).

See also [FIM §](#fim-portal) and chapter 10 vs 11 skill boundary: FIM skill = portal API surface; LeiKa skill = LeiKa identifiers and `source=leika` mapping.

---

## Cross-source identifiers (`raw_payload`)

Keys below are **candidates** for [catalogue task fanout](../../.plans/discovery-layer/chapters/14-catalogue-task-fanout.md) (e.g. enqueue `enrich_metadata` when present). Confirm exact JSON paths from fixtures in chapters 12–13.

| Key / concept | Typical source | Fanout use |
| --- | --- | --- |
| `fim_id` | GovData OZG row | Enrich via FIM when present |
| `redaktion_id`, `leistung_id` | OZG / PVOG / FIM | LeiKa enrich |
| PVOG service / portal ids | OZG JSON, PVOG API | Dedup and `external_id` for `pvog` source |
| `portal_url` / service URL | All ingest paths | `fetch_url` tasks |

Store the full source row in `catalogue_service.raw_payload` for audit.

---

## Related plans

| Chapter | Plan |
| --- | --- |
| 7a | [07a-government-data-sources-canon.md](../../.plans/discovery-layer/chapters/07a-government-data-sources-canon.md) |
| Skills 8–11 | [chapters/](../../.plans/discovery-layer/chapters/) |
| GovData ingest | [12-govdata-ozg-ingest.md](../../.plans/discovery-layer/chapters/12-govdata-ozg-ingest.md) |
| PVOG ingest | [13-pvog-ingest-cli.md](../../.plans/discovery-layer/chapters/13-pvog-ingest-cli.md) |
| Enrich | [17-fim-leika-enrich.md](../../.plans/discovery-layer/chapters/17-fim-leika-enrich.md) |
