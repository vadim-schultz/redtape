---
name: Document Matrix — Architecture
overview: "Contract for organizing documents on two independent axes — domain (what the paper is about) and life situation (the event the user is in) — across data model, Postgres, Litestar API, and the React web app, scoped to Germany."
isProject: true
---

# Document Matrix — Architecture

**Repo:** `redtape` (`apps/api`, `apps/web`).

**Sibling docs:** [01-rollout.md](01-rollout.md) — chapter sequence · [gaps-and-decisions.md](gaps-and-decisions.md) — settled decisions and open seams · [chapters/](chapters/) — executable plans · Related: [data-model chapter](../../docs/planning/directions/data-model-migrations/02-documents-and-requirements.md), [graph resolution](../../docs/planning/directions/data-model-migrations/03-graph-resolution-and-views.md).

**Status:** shipped (chapters 1–10). Open seams: [gaps-and-decisions.md](gaps-and-decisions.md).

---

## 1. Problem statement

The catalog today is a flat list per jurisdiction. [Document](../../apps/api/app/models/document.py) has
a jurisdiction, slug, i18n title/description and URL — nothing says what a paper is *for*. Users do not
arrive with a document name; they arrive with a situation ("we are moving", "I lost my job") or a
topic ("my car", "my boat"). The master summary already promises organization "by domain, life
situation" ([00-master-summary.md](../../docs/planning/00-master-summary.md)) but no plan models it.

This suite adds the two axes as first-class, browsable taxonomies. The dependency graph
(document → required documents) is untouched; the matrix is the **entry point** into it.

---

## 2. Vocabulary (fixed names — use these everywhere)

| Term | German | Meaning | Examples |
| --- | --- | --- | --- |
| **Domain** | Lebensbereich | What area of life a document belongs to | vehicles & mobility, housing, work |
| **Life situation** | Lebenslage | The event or state a user is in | moving house, birth of a child, job loss |
| **Cell** | — | Documents tagged with one domain **and** one situation | *moving house* × *vehicles* → Kfz-Ummeldung |
| **Matrix** | — | The grid of all cells with document counts | rows = situations, columns = domains |

Code names: table/entity `domain`, `life_situation`; API paths `domains`, `life-situations`, `matrix`;
query params `domain`, `situation` (their **codes**, §3). Do not introduce "category", "topic" or "tag" as synonyms.

---

## 3. Model

```mermaid
erDiagram
  DOCUMENT ||--o{ DOCUMENT_DOMAIN : tagged
  DOMAIN ||--o{ DOCUMENT_DOMAIN : groups
  DOCUMENT ||--o{ DOCUMENT_LIFE_SITUATION : tagged
  LIFE_SITUATION ||--o{ DOCUMENT_LIFE_SITUATION : groups
```

| Table | Columns | Constraints |
| --- | --- | --- |
| `domain` | `id` UUID, `code`, `name_i18n` JSONB, `description_i18n` JSONB, `icon`, `sort_order` | `code` unique; `de` + `en` keys on every seeded row, further locales (`fr`, `it`, …) simply add keys |
| `life_situation` | same shape | same |
| `document_domain` | `document_id`, `domain_id` | composite PK; FKs `ON DELETE CASCADE` |
| `document_life_situation` | `document_id`, `life_situation_id` | composite PK; FKs `ON DELETE CASCADE` |

Rules:

- **Many-to-many on both axes.** A birth certificate sits in *family & children* and *identity*, and in
  *birth of a child*, *marriage*, and *moving to Germany*.
- **Cells are computed, never stored.** A cell is the intersection of the two join tables.
- **Taxonomies are global**, not jurisdiction-scoped. Which documents exist in a jurisdiction already
  scopes the matrix ([Document.jurisdiction_id](../../apps/api/app/models/document.py)).
- **No change to `document` or `document_requirement`.** Existing columns and endpoints keep their meaning.
- **i18n** follows the existing pattern: JSONB with `de` and `en`, resolved server-side through
  [locale_resolution.py](../../apps/api/app/locale_resolution.py); clients never receive raw JSONB.
- **Codes, not slugs.** Each term has a `code`: a language-neutral, English-derived, ASCII kebab-case
  identifier (`moving-house`, `birth-of-child`, `vehicles-mobility`) that is **never translated and never
  renamed**. It is the public identifier in query params and API payloads, exactly like translation keys
  in `ui_translation` and `Jurisdiction.code`. All user-facing text comes from `name_i18n`, so adding
  France or Italy means adding `fr` / `it` names, not new URLs. Codes are deliberately not derived from
  German words: a French user following `?situation=umzug` would see a foreign word in their address bar
  and shared links would look like one country's vocabulary. Localized URL paths are an explicit
  non-goal ([gaps-and-decisions.md](gaps-and-decisions.md) D8).
- **Stay on Postgres.** Intersection counts are plain joins; see
  [gaps-and-decisions.md](gaps-and-decisions.md) D5.

---

## 4. Germany seed taxonomy

Finalized in chapter 2. Flat lists, sorted by `sort_order`. The **code** column is the language-neutral
identifier; `de`/`en` are display names. Another country reuses the codes and adds its own locale names
(`fr`, `it`), plus new rows only for concepts that do not exist in Germany (for example a French `pacs`
situation).

### Domains (Lebensbereiche)

| Code | de | en |
| --- | --- | --- |
| `identity-civil-status` | Identität & Personenstand | Identity & civil status |
| `housing` | Wohnen | Housing |
| `vehicles-mobility` | Fahrzeuge & Mobilität | Vehicles & mobility (car, motorbike, boat, licences) |
| `work-employment` | Arbeit & Beruf | Work & employment |
| `family-children` | Familie & Kinder | Family & children |
| `education` | Bildung | Education |
| `health-insurance` | Gesundheit & Versicherung | Health & insurance |
| `taxes-finance` | Steuern & Finanzen | Taxes & finance |
| `residence-migration` | Aufenthalt & Migration | Residence & migration |
| `retirement-old-age` | Rente & Alter | Retirement & old age |
| `self-employment-business` | Selbstständigkeit & Gewerbe | Self-employment & business |
| `social-benefits` | Soziales & Leistungen | Social benefits |
| `law-justice` | Recht & Justiz | Law & justice |

Vehicle kinds (car, motorbike, boat) are **not** separate domains: they are distinct documents inside
`vehicles-mobility` (Kfz-Zulassung, Motorradführerschein, Sportbootführerschein). See D4.

### Life situations (Lebenslagen)

| Code | de | en |
| --- | --- | --- |
| `moving-house` | Umzug | Moving house |
| `birth-of-child` | Geburt eines Kindes | Birth of a child |
| `marriage` | Heirat / Lebenspartnerschaft | Marriage / civil partnership |
| `separation-divorce` | Trennung & Scheidung | Separation & divorce |
| `death-of-relative` | Todesfall | Death of a relative |
| `job-loss` | Jobverlust | Losing a job |
| `new-job` | Berufseinstieg / Jobwechsel | Starting or changing jobs |
| `going-self-employed` | Selbstständig machen | Going self-employed |
| `studying` | Studium | Studying |
| `starting-school` | Einschulung | Starting school |
| `renting-home` | Wohnung mieten | Renting a home |
| `buying-property` | Immobilie kaufen / bauen | Buying or building property |
| `buying-vehicle` | Fahrzeug kaufen / zulassen | Buying and registering a vehicle |
| `getting-licence` | Führerschein / Bootsschein erwerben | Getting a driving or boating licence |
| `immigration` | Zuzug nach Deutschland | Moving to Germany |
| `naturalisation` | Einbürgerung | Naturalisation |
| `illness-care` | Krankheit / Pflegebedürftigkeit | Illness / care needs |
| `retirement` | Renteneintritt | Retirement |

---

## 5. API contract

Layering follows the project rule: **repos → services → controllers → routers**, each layer talking only
to the one below, as in [features/documents/](../../apps/api/app/features/documents/). Framework is
Litestar (see [documents/controller.py](../../apps/api/app/features/documents/controller.py)).

| Method + path | Returns | Notes |
| --- | --- | --- |
| `GET /api/v1/domains` | `[{code, name, description, icon}]` | Locale-resolved, ordered by `sort_order` |
| `GET /api/v1/life-situations` | same shape | same |
| `GET /api/v1/documents?domain=&situation=` | existing `DocumentListResponse` | Both optional, combinable, repeatable per axis; unknown code → 422 |
| `GET /api/v1/documents/{id}` | existing detail + `domains[]`, `life_situations[]` | Additive fields |
| `GET /api/v1/matrix?jurisdiction_id=` | `{total, cells, situations, domains}` (§5.1) | Non-empty cells and axis totals; all counts respect the jurisdiction filter |

A new feature package `features/taxonomy/` owns domains, situations and the matrix. The documents
feature never queries taxonomy tables directly: it calls the taxonomy **service** to resolve codes to
ids (strict layering; a feature's service never reaches into another feature's repo).

---

### 5.1 Matrix response and axis selection

The matrix answers three questions, so its payload carries three lists:

```json
{
  "total":     31,
  "cells":      [{"domain": "housing", "situation": "moving-house", "count": 3}],
  "situations": [{"code": "moving-house", "count": 7}],
  "domains":    [{"code": "housing", "count": 12}]
}
```

- **Cell** — documents tagged with that domain **and** that situation. Selecting it opens
  `/documents?domain=D&situation=S`.
- **Row total (situation)** — *all* documents tagged with that situation, in any domain. Selecting the
  row opens `/documents?situation=S`.
- **Column total (domain)** — *all* documents tagged with that domain, in any situation. Selecting the
  column opens `/documents?domain=D`.
- **Grand total (`total`)** — all documents in scope, tagged or not. Selecting it opens `/documents`.

Axis totals are **distinct documents**, not the sum of cells: a document tagged with two domains
appears in two cells of one row but counts once in that row's total. The UI must never compute totals
by summing cells. `situations` and `domains` list only terms with at least one document in the current
scope, so the grid shows only rows and columns that apply to the selected jurisdiction (a
Germany-only term does not appear for a French municipality). The documents endpoint already accepts a
single axis, so row and column selection need no extra API.

## 6. Frontend

Code lives under `apps/web/src/features/`, one component per file, directory mirroring hierarchy
(existing pattern: [features/documents/](../../apps/web/src/features/documents/)).

| Surface | Where | Job |
| --- | --- | --- |
| Taxonomy client + hooks | `features/taxonomy/{services,hooks,types}` | Typed fetch + TanStack Query, locale-aware keys |
| Matrix overview | `features/taxonomy/containers/MatrixPage`, route `/matrix` | Situations × domains grid. Cell → both filters; row header → situation only; column header → domain only; corner → everything. Headers show distinct-document totals |
| List filters | `features/documents/components/documents-list/` | Domain and situation chips, state in URL search params; a row or column selection arrives as one active chip |
| Tags | `DocumentCard`, `DocumentHeader` | Domain/situation badges, absent when empty |

Rules carried over from [web-frontend/00-architecture.md](../web-frontend/00-architecture.md): Chakra v3
namespace imports, [AppCard](../../apps/web/src/components/data-display/AppCard.tsx) as the card look,
theme tokens only, no hardcoded strings — new keys go into
[apps/api/scripts/seed_data/translations/](../../apps/api/scripts/seed_data/translations/) (`de.json`,
`en.json`) and the web [fallback bundles](../../apps/web/src/i18n/fallback/).

---

## 7. Out of scope

Localized URL paths or per-locale slugs (`/dokumente`, `/documents`, `/documenti`); route paths stay
English constants like `/documents` today, and only *content* is translated.

Dependency-closure endpoints and tree UI (graph-resolution strand), situation checklists,
curation/admin UI and community tagging proposals (social-moderation strand), mobile vault taxonomy
(Flutter, later suite), hierarchical situations.
