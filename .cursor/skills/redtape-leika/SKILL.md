---
name: redtape-leika
description: >-
  LeiKa (Leistungskatalog) identifiers, bulk Kataloge exports, and
  source=leika stammtext mapping for discovery enrich. Use when implementing
  chapter 17 LeiKa enrich or resolving leika_key / redaktion_id / leistung_id
  from GovData or PVOG rows into FIM stammtext calls.
---

# LeiKa (discovery enrich)

Staging contract:
[`.plans/discovery-layer/02-staging-model-and-api.md`](../../../.plans/discovery-layer/02-staging-model-and-api.md)
(§8 CoS skills, logical `discovery_source=leika`, enrich via chapter 17 — not catalogue ingest).

**Enrich implementation:** [chapter 17](../../../.plans/discovery-layer/chapters/17-fim-leika-enrich.md)
(same FIM host as `redtape-fim`; `FIM_PORTAL_BASE_URL`).

## When to use

- Chief-of-staff or chapter-implementer work on **LeiKa enrich** (`discovery_source=leika`).
- You need LeiKa **`external_id` convention**, `leika_key` (14-digit service key), or how **`source=leika`** stammtext path segments map to **`discovery_entity` / `discovery_claim`** and catalogue `raw_payload` fanout keys.
- You are **not** documenting the full FIM Portal route surface (see `redtape-fim`), ingesting GovData OZG rows (`redtape-govdata`), or ingesting PVOG Suchdienst lists (`redtape-pvog`).

**Boundary with chapter 10:** LeiKa has **no separate HTTP host** (D14). Use FIM Portal REST and Kataloge bulk exports only. HTTP paths, OpenAPI, and steckbrief routes live in `redtape-fim`.

**Ingest vs enrich:** `leika` is **enrich only** — resolve identifiers from existing catalogue rows (`govdata`, `pvog`), then fetch LeiKa stammtext via FIM with `source=leika`.

## Authoritative documentation

Endpoint tables, env defaults, and cross-source `raw_payload` keys live in the checked-in canon — do not duplicate full path registries here:

[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § LeiKa.

| Resource | URL |
| --- | --- |
| Kataloge (LeiKa-plus, CSV/XZuFi) | https://fimportal.de/kataloge |
| FIM Swagger (stammtext with `source=leika`) | https://fimportal.de/docs |
| FIM data sources matrix | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |
| PVOG LeiKa lookup (secondary ids) | https://pvog.fitko.net/suchdienst/api/swagger-ui/index.html |

OpenAPI for stammtext: `GET {FIM_PORTAL_BASE_URL}/openapi.json` — confirm `{source}` enum includes `leika` (see `redtape-fim`).

## API access (no separate LeiKa host)

| Use | Entry |
| --- | --- |
| **Stammtext (primary API path)** | `GET /api/v1/leistung-stammtexte/{redaktion_id}/{leistung_id}/leika` under `{FIM_PORTAL_BASE_URL}` (default `https://fimportal.de`) |
| **Stammtext search** | `GET /api/v1/leistung-stammtexte` with filters per OpenAPI |
| **Bulk LeiKa-plus / Alle Leistungen** | https://fimportal.de/kataloge — XZuFi 2.2.0 / CSV exports (offline analysis; not the default HTTP enrich client) |
| **Secondary id resolution** | PVOG `GET /v3/servicedescriptions/leikaid` when OZG or Suchdienst rows already carry LeiKa keys |

**`source` enum value (stammtext path segment):** `leika`.

## Authentication

Same as FIM public read enrich: no API key on default `GET` stammtext paths. Machine API entity/claim upserts require `DISCOVERY_API_KEY` and `DISCOVERY_API_URL` (chapter 17).

## Rate limits

No published LeiKa-specific quota. Use modest concurrency, backoff on **`429`** / **`503`**, and honor **`Retry-After`**. **CI and unit tests use fixtures only** — no live FIM or PVOG network in `./ci.sh`.

## Corporate network (manual Kataloge / Swagger)

On R&S laptops, export `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` before `curl`, browser Swagger, or manual enrich runs. See
[corporate-build-env.md](../chief-of-staff/corporate-build-env.md) and canon § Corporate network.

## Identifier fields (JSON → path segments)

Map FIM stammtext path segments from source-native names in ingest `raw_payload`:

| Concept | Typical JSON fields | Notes |
| --- | --- | --- |
| Redaktion | `redaktion_id`, `redaktionId` | FIM redaktion segment |
| Leistung | `leistung_id`, `leistungId`, `lbId` | FIM leistung segment; PVOG `lbId` on relations |
| LeiKa service key | `leika_key`, entries in `leikaIds` | Often 14 digits on GovData OZG rows; fanout may set `leistung_id` from `leika_key` per canon |
| Stammtext source | `source` | Must be `leika` for LeiKa stammtext URL |

**Fixture convention (chapter 17):** store representative stammtext under `apps/discovery-ingest/tests/fixtures/leika/` with `source=leika` in path or payload metadata.

## Example stammtext fragment (truncated)

```json
{
  "redaktion_id": "RED-EXAMPLE",
  "leistung_id": "LB-EXAMPLE-001",
  "source": "leika",
  "titel": "Beispiel-Leistung (LeiKa)",
  "kurztext": "Kurzbeschreibung …"
}
```

Store the **full FIM stammtext JSON** in enrich snapshots (`raw_payload` on related catalogue rows or entity metadata per chapter 17).

## `external_id` convention

**external_id convention (staging):** stable id for enrich-side rows tied to LeiKa; align path segments with FIM stammtext URLs.

`leika:{redaktionId}:{leistungId}`

| Segment | Source field | Notes |
| --- | --- | --- |
| `redaktionId` | `redaktion_id` / `redaktionId` in FIM or fanout payload | Required for stammtext path |
| `leistungId` | `leistung_id` / `leistungId` / parsed from `leika_key` | Required for stammtext path |

Examples:

- `leika:RED-EXAMPLE:LB-EXAMPLE-001`
- Do **not** use the 14-digit `leika_key` alone as `external_id` when canon expects redaktion + leistung segments — resolve segments via fanout, bulk export, or PVOG LeiKa lookup first.

When enrich is keyed by FIM steckbrief instead of LeiKa segments, prefer `fim:{leistungsschluessel}` from `redtape-fim` and treat LeiKa as supplementary metadata in `raw_payload`.

## Mapping

LeiKa enrich **does not** call `POST /catalogue/batch`. It reads existing `catalogue_service` rows, resolves LeiKa identifiers, fetches stammtext with **`source=leika`**, then upserts **`discovery_entity`** and **`discovery_claim`** via the machine API (chapter 17).

| Input / response | Discovery target | Notes |
| --- | --- | --- |
| (constant) | enrich provenance | Logical source `leika`; HTTP host is still FIM Portal |
| see § `external_id` convention | entity / claim stable keys | max 200 chars where stored as string ids |
| `titel` / title fields | claim or entity display metadata | map to i18n shape expected by machine API |
| `kurztext`, long text fields | claim `metadata` / description stubs | chapter 17 maps to suggestion-oriented stubs |
| entire stammtext object | enrich `raw_payload` | include keys below for fanout and audit |

**`raw_payload` keys from upstream ingest** (canon § Cross-source identifiers — copy source-native names):

| Field | Source | Fanout / enrich use |
| --- | --- | --- |
| `leika_key` | GovData OZG JSON | LeiKa / FIM enrich; alias to `leistung_id` when parsing rules apply |
| `leikaIds` | PVOG onlinedienste list | Secondary LeiKa keys |
| `redaktion_id`, `leistung_id` | OZG / PVOG / FIM fanout | Build stammtext URL with `source=leika` |
| `source` | Stammtext response | Must include `leika` for this skill’s HTTP path |
| `lbId` | PVOG relations | Leistung segment candidate |

**PVOG secondary lookup:** when only a LeiKa id is known, `GET /v3/servicedescriptions/leikaid` (Suchdienst base `PVOG_API_BASE_URL`) can yield `lbId` and related ids before calling FIM stammtext — see `redtape-pvog` for Suchdienst auth and deprecations.

## Verification (skill + URLs)

After editing this skill, run the discovery skill checker (validates headings, staging link, canon link, and at least three `https://` URLs):

```bash
./scripts/check_discovery_skills.sh leika
```
