---
name: redtape-pvog
description: >-
  PVOG Suchdienst REST API auth, pagination, deprecations, and catalogue batch
  mapping for discovery ingest. Use when implementing chapter 13 PVOG CLI or
  mapping Suchdienst responses to POST /api/v1/discovery/machine/catalogue/batch.
---

# PVOG Suchdienst (discovery ingest)

Staging contract:
[`.plans/discovery-layer/02-staging-model-and-api.md`](../../../.plans/discovery-layer/02-staging-model-and-api.md)
(§3 `catalogue_service`, machine route `POST /catalogue/batch`).

**Ingest implementation:** [chapter 13](../../../.plans/discovery-layer/chapters/13-pvog-ingest-cli.md)
(`python -m discovery_ingest pvog run`).

## When to use

- Chief-of-staff or chapter-implementer work on **PVOG catalogue ingest** (`discovery_source=pvog`).
- You need Suchdienst base URLs, pagination (`nextPageToken` / `next` links), deprecation rules, or the **batch upsert DTO** for the discovery machine API.
- You are **not** ingesting the GovData OZG JSON mirror (see `redtape-govdata`) or running FIM/LeiKa enrich (see `redtape-fim` / `redtape-leika`).

Prefer **current** `servicedescriptions` and `onlineservices` families from OpenAPI; avoid paths listed on the deprecations page.

## Authoritative documentation

Endpoint tables, excluded paths, and `raw_payload` keys live in the checked-in canon — do not duplicate full path registries here:

[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § PVOG.

| Resource | URL |
| --- | --- |
| Product portal | https://pvog.fitko.de/ |
| API base (default D13) | `https://pvog.fitko.net/suchdienst/api` (`PVOG_API_BASE_URL`) |
| Swagger UI | https://pvog.fitko.net/suchdienst/api/swagger-ui/index.html |
| OpenAPI 3 | https://pvog.fitko.net/suchdienst/api/v3/api-docs |
| Deprecations | https://pvog.fitko.de/api/deprecations/ |
| Bereitstelldienst (optional bulk) | `https://pvog.fitko.net/bereitstelldienst/api` + Client ID on portal |

## API base URLs

| Use | Base / entry |
| --- | --- |
| **Suchdienst (chapter 13 default)** | `https://pvog.fitko.net/suchdienst/api` — override with `PVOG_API_BASE_URL` (no trailing slash before path segments) |
| OpenAPI | `GET /v3/api-docs` under Suchdienst base |
| **Bereitstelldienst (optional bulk)** | `https://pvog.fitko.net/bereitstelldienst/api` — requires Client ID from [PVOG portal Ressourcen](https://pvog.fitko.de/); not required for v1 loop ingest |

**Chapter 13 default list paths** (confirm against Swagger before production ingest):

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/v7/servicedescriptions/{ars}` | Leistungen for ARS (major list) |
| `GET` | `/v1beta2/onlineservices` | Onlinedienste in ARS scope (`ars`, optional `leikaIds`, `nextPageToken`) |
| `GET` | `/v6/servicedescriptions/{lbid}/detail` | Leistung detail by `lbId` |
| `GET` | `/v2/onlineservices/detail` | Onlinedienst detail (`q` = onlinedienst id) |

## Authentication

**Suchdienst (search API):** public read for the endpoints used in chapter 13. No API key or Client ID on the default ingest path.

**Bereitstelldienst:** registered **Client ID** from the PVOG product portal (Ressourcen). Use only when you intentionally ingest via bulk Bereitstelldienst APIs — out of scope for v1 loop unless explicitly requested.

Machine API upserts require `DISCOVERY_API_KEY` and `DISCOVERY_API_URL` (chapter 13), same as GovData ingest.

## Deprecations and `X-PVOG-DEPRECATED`

- Do **not** call Suchdienst or Bereitstelldienst paths listed on the [deprecations page](https://pvog.fitko.de/api/deprecations/).
- On any response, if header **`X-PVOG-DEPRECATED: true`** is present, treat the endpoint as deprecated: log at warning, stop using that path in new code, and migrate to the replacement documented on the deprecations page.
- Ingest clients should fail closed in CI on fixtures that simulate deprecated routes only when testing deprecation handling; production crawls should skip deprecated URLs.

Excluded paths (examples — full list in canon): `/v2/locations`, `/v5/servicedescriptions/{ars}/detail`, Bereitstelldienst `/v2/verwaltungsobjekte`.

## Rate limits

No published hard quota. Use modest concurrency, backoff on `429`/`503`, and respect `Retry-After` when present. **CI and unit tests use fixtures only** — no live PVOG network in `./ci.sh`.

## Corporate network (manual Suchdienst / Swagger)

On R&S laptops, export `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` before `curl`, browser Swagger, or manual ingest runs. See
[corporate-build-env.md](../chief-of-staff/corporate-build-env.md) and canon § Corporate network.

**httpx (`apps/discovery-ingest`):** use default `trust_env=True` so proxy env vars apply in manual runs.

## Pagination

**Onlinedienste (`/v1beta2/onlineservices`):** cursor via query parameter `nextPageToken`. Repeat until the response omits `nextPageToken` or returns an empty item list.

**Leistungen lists (`/v7/servicedescriptions/{ars}`):** follow pagination fields documented in OpenAPI for the active major version (page index, `next` link, or token — mirror the shape you implement in the client).

**Fixture convention (chapter 13):** store representative pages under `apps/discovery-ingest/tests/fixtures/pvog/` — for example `page1.json` with a `nextPageToken` and a second page file for link-following tests. Do not commit live API dumps with personal data.

## Example Suchdienst fragment (truncated)

Beta onlinedienste list shape (field names vary by version; store the **full row** in `raw_payload`):

```json
{
  "onlineservices": [
    {
      "id": "OD-EXAMPLE-001",
      "title": "Beispiel-Onlinedienst",
      "links": [{ "rel": "self", "uri": "https://example.egov.de/online" }],
      "relations": [{ "lbId": "LB-EXAMPLE-001", "ars": "000000000000" }]
    }
  ],
  "nextPageToken": "eyJwYWdlIjoyfQ=="
}
```

Leistung detail responses expose `lbId`, LeiKa keys, and nested `relations`; map titles and URLs from the detail payload used by your ingest slice.

## Environment variables

| Variable | Default | Role |
| --- | --- | --- |
| `PVOG_API_BASE_URL` | `https://pvog.fitko.net/suchdienst/api` | Suchdienst REST prefix |
| `DISCOVERY_API_URL` | (required for ingest) | Redtape discovery machine API base |
| `DISCOVERY_API_KEY` | (required for ingest) | `X-API-Key` for batch upsert |
| PVOG Client ID | (portal only) | Bereitstelldienst bulk — not for default Suchdienst ingest |

## `external_id`

Stable id for `(source, external_id)` uniqueness:

`pvog:{portal_id}:{service_id}`

| Segment | Source field (Swagger) | Notes |
| --- | --- | --- |
| `portal_id` | Onlinedienst id — `id` in list/detail, or `odId` path segment | Portal / onlinedienst scope |
| `service_id` | Leistung id — `lbId` in relations and detail paths | Use the Leistung key when ingesting Leistungen; for onlinedienst-only rows use the onlinedienst `id` as both segments only when Leistung is absent (document in ingest mapper) |

Examples:

- `pvog:OD-EXAMPLE-001:LB-EXAMPLE-001`
- Federal ARS `000000000000` is **jurisdiction** scope on queries, not part of `external_id`.

Never omit `external_id`; batch items without it must be rejected in ingest (chapter 13).

## Mapping

Map each ingested **Leistung** or **Onlinedienst** row (per chapter 13 slice) to `CatalogueBatchItem` (`source` must be `pvog`). Resolve `jurisdiction_id` from CLI `--jurisdiction-id` or from `ars` on the row via jurisdiction lookup.

| PVOG / Suchdienst field | `catalogue_service` / batch field | Notes |
| --- | --- | --- |
| (constant) | `source` | `pvog` |
| see § `external_id` | `external_id` | max 200 chars |
| CLI / `ars` → lookup | `jurisdiction_id` | UUID FK |
| `title` / `name` / localized label | `title_i18n` | at least `{"de": "…"}` |
| description fields from detail | `description_i18n` | optional |
| `links[].uri` or service URL | `portal_url` | triggers `fetch_url` task on upsert when set |
| entire response object | `raw_payload` | include `id`, `lbId`, `ars`, `leikaIds`, `relations` for fanout |

**`raw_payload` keys for task fanout** (canon § Cross-source identifiers):

| Field | Fanout use |
| --- | --- |
| `id` | Onlinedienst id (`odId`) |
| `lbId` | Leistung id in relation payloads |
| `ars` | Regional scope |
| `leikaIds` | LeiKa enrich |
| `relations` | Links between onlinedienst and Leistung |

## Example batch upsert body

`POST /api/v1/discovery/machine/catalogue/batch` — up to 50 items per request.

```json
{
  "items": [
    {
      "source": "pvog",
      "external_id": "pvog:OD-EXAMPLE-001:LB-EXAMPLE-001",
      "jurisdiction_id": "00000000-0000-0000-0000-000000000001",
      "title_i18n": { "de": "Beispiel-Leistung" },
      "description_i18n": { "de": "Kurztext …" },
      "portal_url": "https://example.egov.de/online",
      "raw_payload": {
        "id": "OD-EXAMPLE-001",
        "lbId": "LB-EXAMPLE-001",
        "ars": "000000000000",
        "leikaIds": ["12345678901234"],
        "relations": []
      }
    }
  ]
}
```

Replace `jurisdiction_id` with the real UUID from your database lookup.

## Verification (skill + URLs)

After editing this skill, run the discovery skill checker (validates headings, staging link, canon link, and at least three `https://` URLs):

```bash
./scripts/check_discovery_skills.sh pvog
```
