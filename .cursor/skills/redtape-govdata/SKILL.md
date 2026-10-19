---
name: redtape-govdata
description: >-
  GovData CKAN and OZG Leistungen JSON access for discovery catalogue ingest.
  Use when mapping OZG rows to POST /api/v1/discovery/machine/catalogue/batch
  or authoring chapter 12 govdata CLI.
---

# GovData / OZG (discovery ingest)

Staging contract:
[`.plans/discovery-layer/02-staging-model-and-api.md`](../../../.plans/discovery-layer/02-staging-model-and-api.md)
(§3 `catalogue_service`, machine route `POST /catalogue/batch`).

**Ingest implementation:** [chapter 12](../../../.plans/discovery-layer/chapters/12-govdata-ozg-ingest.md)
(`python -m discovery_ingest govdata run`).

## When to use

- Chief-of-staff or chapter-implementer work on **GovData / OZG federal catalogue ingest** (`discovery_source=govdata`).
- You need CKAN package metadata, the **Leistungen** JSON feed URL, or the **batch upsert DTO** shape for the discovery machine API.
- You are **not** calling PVOG Suchdienst (see `redtape-pvog`) or FIM enrich (see `redtape-fim` / `redtape-leika`).

Dataset content is **PVOG-derived** metadata republished on GovData; cross-refs in `raw_payload` may point to PVOG/LeiKa/FIM enrich (chapter 14 fanout).

## Authoritative documentation

Full URL tables, resource UUIDs, env defaults, and `raw_payload` keys live in the checked-in canon — do not duplicate URL registries here:

[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § GovData.

| Resource | URL |
| --- | --- |
| Portal | https://data.gov.de/ |
| CKAN Action API | https://ckan.govdata.de/api/3/action/ |
| OZG primary dataset | https://www.govdata.de/suche/daten/ozg-leistungen-und-zugehorige-onlinedienste |
| CKAN API guide | https://docs.ckan.org/en/latest/api/ |

## API base URLs

| Use | Base / entry |
| --- | --- |
| CKAN Action API | `https://ckan.govdata.de/api/3/action/` (override with `GOVDATA_CKAN_BASE_URL`, default `https://ckan.govdata.de/api/3/action`) |
| Package metadata | `package_show?id={GOVDATA_PACKAGE_ID}` — default id `ozg-leistungen-und-zugehorige-onlinedienste` |
| **Leistungen JSON (CKAN resource)** | `https://api.ozg-umsetzung.de/api/public/v1/dash/open-pvog?order=asc&page={page}&size={size}` |
| **Leistungen JSON (scheduled ingest default)** | `.../open-pvog/000000000000?...&includeAbove=false&includeBelow=false` (`GOVDATA_OPEN_PVOG_ARS`) |
| REST OpenAPI descriptor | `https://api.ozg-umsetzung.de/api/v3/api-docs/dashboard-digitale-verwaltung` |

CKAN mirror (optional): `https://www.govdata.de/ckan/api/3/action/`.

## Authentication

Public read for CKAN Action API and the OZG **open-pvog** Leistungen feed. No API key for v1 ingest.

Machine API upserts require `DISCOVERY_API_KEY` and `DISCOVERY_API_URL` (chapter 12).

## Rate limits

No published hard quota. Use modest page sizes (for example `size=100`), backoff on `429`/`503`, and avoid hammering CKAN in tight loops. **CI and unit tests use fixtures only** — no live GovData network in `./ci.sh`.

## Corporate network (manual CKAN / live JSON)

On R&S laptops, export `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` before `curl`, browser CKAN, or manual ingest runs. See
[corporate-build-env.md](../chief-of-staff/corporate-build-env.md) and canon § Corporate network.

## Pagination

**Leistungen feed:** `page` (0-based) and `size` on `open-pvog` or `open-pvog/{ars}`. Scheduled ingest scopes to Bund (`000000000000`) with `includeAbove=false` and `includeBelow=false`. Stop when a page returns fewer than `size` rows or an empty list.

**CKAN:** use `package_show` once per run for resource metadata; bulk row download for ingest should use the Leistungen API above (not repeated `resource_show` per row).

## Example Leistungen JSON (truncated)

```json
{
  "content": [
    {
      "leika_key": "99003007001000",
      "leika_name": "Erlaubnis für die Teilnahme am Betäubungsmittelverkehr beantragen",
      "ars": "000000000000",
      "leika_bezeichnung": "Erlaubnis zum Verkehr mit Betäubungsmitteln Erteilung",
      "ozgid": 10641,
      "ozg_bezeichnung": "Betäubungsmittelanzeigen und -genehmigungen",
      "url": "https://verwaltung.bund.de/leistung/example",
      "online_status": "ok"
    }
  ],
  "page": { "size": 100, "number": 0, "totalElements": 960, "totalPages": 10 }
}
```

Field names in production exports may include additional PVOG keys; store the **full row** in `raw_payload` and map stable columns below.

## Environment variables

| Variable | Default | Role |
| --- | --- | --- |
| `GOVDATA_CKAN_BASE_URL` | `https://ckan.govdata.de/api/3/action` | CKAN Action API prefix (no trailing slash on action name) |
| `GOVDATA_PACKAGE_ID` | `ozg-leistungen-und-zugehorige-onlinedienste` | `package_show` id for OZG dataset |
| `GOVDATA_OPEN_PVOG_ARS` | `000000000000` | ARS path segment; federal Bund scope for `govdata fetch` |
| `DISCOVERY_API_URL` | (required for ingest) | Redtape discovery machine API base |
| `DISCOVERY_API_KEY` | (required for ingest) | `X-API-Key` for batch upsert |

## `external_id`

Prefer a stable id that survives re-imports:

1. **LeiKa key (OpenPvogDto default):** `govdata:leika:{leika_key}` when `leika_key` is present (unique per row; `ozgid` is a group id shared by many rows).
2. **OZG group id:** `govdata:ozg:{ozgid}` only when `leika_key` is absent.
3. **CKAN resource row:** `govdata:{dataset_id}:{resource_id}:{stable_row_key}` for file-index ingest (rare).

Never omit `external_id`; batch items without it must be rejected in ingest (chapter 12).

## Mapping

Map each OZG **Leistungen** object to `CatalogueBatchItem` (`source` must be `govdata`). Resolve `jurisdiction_id` from `ars` (federal `000000000000` → Germany country jurisdiction in seed/lookup — chapter 12).

| GovData / OZG field | `catalogue_service` / batch field | Notes |
| --- | --- | --- |
| (constant) | `source` | `govdata` |
| see § `external_id` | `external_id` | max 200 chars |
| `ars` → lookup | `jurisdiction_id` | UUID FK; not stored on row |
| `leika_name`, `leistungsname`, `title`, or `name` | `title_i18n` | at least `{"de": "…"}` |
| `beschreibung`, `description`, `leika_bezeichnung`, or `ozg_bezeichnung` | `description_i18n` | optional |
| `url` | `portal_url` | triggers `fetch_url` task on upsert when set |
| entire row object | `raw_payload` | include `leika_key`, `ozgid`, `ars`, `online_status`, `url` for fanout |

**`raw_payload` keys for task fanout** (copy source-native names; see canon § Cross-source identifiers):

| Field | Fanout use |
| --- | --- |
| `leika_key` | LeiKa / FIM enrich; alias `leistung_id` when parsing segments |
| `ozgid` | OZG grouping |
| `url` | `fetch_url` |
| `ars` | jurisdiction scope |
| `online_status` | availability signal |

## Example batch upsert body

`POST /api/v1/discovery/machine/catalogue/batch` — up to 50 items per request.

```json
{
  "items": [
    {
      "source": "govdata",
      "external_id": "govdata:ozg:OZ-EXAMPLE-001",
      "jurisdiction_id": "00000000-0000-0000-0000-000000000001",
      "title_i18n": { "de": "Beispiel-Leistung" },
      "description_i18n": { "de": "Kurztext …" },
      "portal_url": "https://example.bund.de/leistung",
      "raw_payload": {
        "leika_key": "12345678901234",
        "ozgid": "OZ-EXAMPLE-001",
        "ars": "000000000000",
        "url": "https://example.bund.de/leistung",
        "online_status": "ok",
        "leistungsname": "Beispiel-Leistung"
      }
    }
  ]
}
```

Replace `jurisdiction_id` with the real UUID from your database lookup.

## CKAN `package_show` (metadata only)

```http
GET https://ckan.govdata.de/api/3/action/package_show?id=ozg-leistungen-und-zugehorige-onlinedienste
```

Use the response to confirm resource names and UUIDs; primary ingest still uses the **open-pvog** Leistungen JSON URL in canon.
