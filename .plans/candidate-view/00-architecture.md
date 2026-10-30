---
name: "Candidate view — Architecture"
overview: "A public, read-only view of staged document candidates: a ranked list and an item page with ingress and egress dependency cards and a flow diagram, backed by one completeness read model that the admin documents table shares; plus the screenshot collection that makes the pages worth looking at, and distinct admin catalogue and coverage pages."
isProject: false
---

# Candidate view — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Live runs:** [02-live-runs.md](02-live-runs.md) · **Chapters:** [chapters/](chapters/) · **Ledger:** [run-ledger.md](run-ledger.md) · **Parents:** [extraction](../extraction/00-architecture.md), [crawlers](../crawlers/00-architecture.md), [web-gui-harmonization](../web-gui-harmonization/00-architecture.md)

## 1. Why

The crawlers and extraction suites stage **document candidates** (`discovery_document_candidate`) with mentions, requirement edges, domain and life-situation codes, rendered HTML snapshots and (by design) screenshots of the source pages. The only way to look at them is `/admin/discovery/documents`, which is technical, guarded by the admin allowlist, and does not meet the DataTable contract of the harmonization suite (the toolbar sits outside the table, three of six columns sort, none filters in the header, the Title column is unbounded, and nothing says which candidates are "ready"). On 2026-10-30 production held 58 touched candidates, 6 with a domain code, none with a life-situation code, and **no screenshot**: the `capture_screenshot` tasks that `llm_extract` queues are in no default drain kind and nobody drained them.

This suite does five things:

1. Collects the screenshots (a requeue tool and a chief-of-staff live run).
2. Computes **completeness** per candidate once, in one read model.
3. Exposes a **public** candidate list and item view (and the same flags to the admin list).
4. Repairs the admin documents table, and makes the admin catalogue and coverage pages distinct.
5. Hand-completes a handful of the highest-ranking candidates (tags, edges, screenshot) so the new pages can be checked against realistic, fully populated data (section 12).

Nothing here emits, votes, moderates or edits. It is a read surface.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Candidate** | A staged `discovery_document_candidate`: a document name the extraction found on one or more procedure pages. Status `staged` or `emitted`; both are shown. |
| **Procedure** | A catalogue row (`catalogue_service`) a candidate is mentioned on. Artifacts hang off the procedure, not the candidate. |
| **Completeness** | Five boolean flags per candidate (section 3) and their count, 0 to 5. `complete` means all five. |
| **Ingress** | The documents a candidate **requires**: edges where the candidate is the `parent`. Arrows run *into* the candidate. Plain-language label: "needed first". |
| **Egress** | The documents that **require** the candidate: edges where the candidate is the `required` end. Arrows run *out of* the candidate. Plain-language label: "needed by". |
| **Neighbour card** | A compact card for an ingress or egress document: title, optional description line, the edge's condition and optional badge, linking to that candidate's item page. |
| **Manual curation** | A mention or edge written by a curator, with `extractor = 'manual'`. Manual tags are authoritative for the axis they cover (section 3). |
| **Showcase candidate** | One of the five to eight real candidates completed by hand for UI checks (section 12). |
| **Flow diagram** | The ingress column, the central card and the egress column joined by smooth arrows (section 7). |

The stored edge direction is unchanged (`parent_candidate_id` requires `required_candidate_id`). Ingress and egress are a reading of it, fixed in [gaps-and-decisions.md](gaps-and-decisions.md) (D2).

## 3. Completeness model

One repository query (chapter 2) computes, per candidate:

| Flag | True when |
| --- | --- |
| `has_domain` | The candidate has at least one **accepted** domain code: counted over distinct procedures, at least `discovery_tag_min_procedures` (2) procedures and at least `discovery_tag_min_share` (0.5) of the procedures that carry any domain code. This is the rule of `aggregate_tags` in `features/discovery/tags.py`, re-expressed in SQL. |
| `has_situation` | The same rule for life-situation codes. |
| `has_edges` | At least one edge row has the candidate as parent or as required. |
| `has_snapshot` | At least one procedure that mentions the candidate has an `html_snapshot` artifact. |
| `has_screenshot` | At least one procedure that mentions the candidate has a `screenshot` artifact. |

`completeness` is the number of true flags; `complete` is `completeness == 5`. The SQL is the only place the rule lives for listing; a **parity test** runs the same fixtures through `aggregate_tags` and the SQL and requires equal answers, so the two cannot drift. The emit preview and its skip reasons (`no_source_url`, `duplicate`, ...) stay the authority for emission; "ready" in this suite means the five flags and nothing else.

**Manual override (D18).** A mention with `extractor = 'manual'` and non-empty codes for an axis is authoritative: the accepted codes of that axis are exactly the union of its manual codes, whatever the extracted mentions say, and one procedure suffices. Axes are independent. Without a manual mention the consensus above applies unchanged. The Python reference (`curated_codes` beside `aggregate_tags`) and the SQL implement the same rule and share a parity table.

Default order of the list: `completeness` descending, then `mentions` descending, then the existing deterministic title/key/id tie-break. The public list shows **every** candidate (decision D1); `filter[complete]=yes` narrows it.

## 4. Public API (chapter 3)

New package `apps/api/app/features/candidates/`, DTOs in `apps/api/app/schema/candidate/`. The controller has **no guards** (a public route is a controller without `guards`); read-only; never returns mention internals that are not needed.

| Route | Returns |
| --- | --- |
| `GET /api/v1/candidates` | `{items, total, offset, limit}` of `CandidateCard`. List-query spec: `sort_by` in `completeness`, `title`, `mentions`, `created_at`; `filter[complete]` (`yes`/`no`), `filter[domain]`, `filter[situation]` (taxonomy codes, unknown code is a 422); `q` over titles. Paging via `PageParams`. |
| `GET /api/v1/candidates/{id}` | `CandidateDetail`: title, description, status, tags with localized names, the five flags, `ingress[]`, `egress[]` (each a `CandidateNeighbour`), `sources[]` (procedure title, portal URL, role, excerpt), `screenshot` (`{url, fetched_at}` or null). |
| `GET /api/v1/candidates/{id}/screenshot` | The newest screenshot of the candidate's procedures, streamed from the object store: `Content-Type` as stored, `Cache-Control: public, max-age=31536000, immutable`, `ETag` = the artifact's sha256 (`If-None-Match` answers 304). 404 when there is none; 503 when the R2 read budget is spent. |

`CandidateCard`: `id`, `key`, `title` (localized), `description`, `domains[]`, `situations[]` (accepted codes with names), `status`, `completeness`, `complete`, `flags` (`has_domain`, `has_situation`, `has_edges`, `has_snapshot`, `has_screenshot`), `mention_count`. Titles resolve with `app/i18n_resolution.py` (requested locale, `de`, `en`, any). **Description** has no column on a staged candidate; it is the best mention excerpt (role order `required`, `form`, `issued`, then oldest, at most 300 characters) with `description_source` set to the procedure title (D4).

Tags on a card are the **accepted** consensus codes only, resolved against `Domain` and `LifeSituation` for names. A candidate with raw mention codes below the support rule shows none.

The admin list (chapter 4) reuses the same completeness query and adds the flags to `CandidateListItemRead`; it keeps its own guards, legacy parameters and routes.

## 5. Web surface

New feature `apps/web/src/features/candidates/` in the house layout (`containers`, `components/<X>View/` folders with barrels, `hooks`, `services`, `types`, `utils`). Query keys in `src/app/queryKeys.ts` (`candidates` group, locale in the key). Strings in `src/i18n/fallback/{en,de}.json` under `candidates.*`. Routes, public, in `src/app/routes.tsx` next to `/documents`: `/candidates` and `/candidates/:id`, each with its own `Suspense` skeleton. The app menu's `DocumentsMenuRow` gets a third `MenuIconLink`.

| Screen | Content |
| --- | --- |
| `/candidates` | Page title, "staged, unreviewed" banner, search, domain and situation chips (reusing the taxonomy hooks of `features/documents`), a "complete only" switch, the list as `AppCard`s (the front-page card style) each with its completeness chips and tags, Chakra pagination, explicit loading, empty, error states. |
| `/candidates/:id` | Header: title, description with "from the source page: {procedure}" attribution, tags, completeness checklist. Section **Ingress** (cards), section **Egress** (cards). Section **Flow** (diagram). Section **Evidence**: screenshot and sources. Skeleton, error and not-found states; the same banner. |

## 6. Cards

Neighbour and list cards are the existing `AppCard` (`src/components/data-display/AppCard.tsx`) with the `DocumentCard` typography (`subsectionHeader` title, `Card.Description`). New `CandidateCard` composes it with a `CompletenessChips` row. The neighbour variant adds the edge's condition text and an "optional" badge and is a **compact fixed-height** variant so the diagram can place arrows by arithmetic.

## 7. Flow diagram

Cheapest to render: **hand-rolled SVG, no dependency** (the app has no graph library; reactflow or d3 would be the first). Layout is a pure function:

```text
layoutFlow(ingressCount, egressCount, geometry) -> { height, nodes, paths }
```

- Three columns: ingress cards (left), the central card (middle), egress cards (right). Each column is a vertical stack of equal-height compact cards with a fixed gap, vertically centred against the taller column.
- Every card has a computed `y`; an arrow is a cubic Bezier `M x1 y1 C xm y1, xm y2, x2 y2` between the right edge of an ingress card and the left edge of the centre card (converging), and between the centre card's right edge and each egress card's left edge (diverging). Horizontal control points give the smooth S-curve; an arrowhead is an SVG `marker`.
- The HTML cards and the SVG paths share the same geometry constants, so nothing is measured in the DOM and the function is unit-testable in jsdom (counts of nodes and paths, endpoints on card edges, empty columns, one-sided graphs).
- With no ingress and no egress the section shows a short "no dependencies staged" note instead of an empty diagram.
- Below the `md` breakpoint the diagram is hidden and the two card lists above it carry the information. The SVG is `role="img"` with a text alternative ("{n} documents needed first, {m} needed by"); the cards stay real links in DOM order.
- Colors come from semantic tokens (`border`, `fg.muted`, brand accent for the centre card) so it works in light and dark.

## 8. Admin documents table (chapters 4 and 8)

The shared `DataTable` kernel already supports `canSort` and a per-column `filter`; the candidates table simply never declared them. Target:

- **Toolbar in the table header.** Search and "clear filters" live in a header slot of `DiscoveryDataTable`'s `SectionCard`; per-column filters use the kernel's header popovers and appear as removable chips (`ActiveFilters`), which they never did before because no column declared a filter.
- **Every column sorts and filters.** Title (sort, contains), Jurisdiction (sort, eq), Roles (eq), Mentions (sort, `gte`), Status (sort, eq), First seen (sort), and the new **Readiness** column (completeness chips; sort by `completeness`, filter `complete`). A "Ready" quick filter sets `filter[complete]=yes`. The API (chapter 4) allowlists every key.
- **Bounded Title.** `DataTableColumn` gains an optional `maxWidth`; a `TruncatedText` cell clips with an ellipsis and shows the full title in a Chakra `Tooltip` (the app's first; `components/ui/tooltip.tsx` snippet). The cell keeps its link and a native `title` fallback is not used. The same cell bounds the tasks "target" column.
- Response totals describe the full filtered result; changing search, filter or sort resets to page one (existing kernel behaviour).

## 9. Admin catalogue and coverage (chapter 9)

Both pages render `CoverageSummary` (8 cards) today; the catalogue's own `summary` (`total`, `by_source`, `by_pipeline_stage`) is typed but never shown. Target:

- **Coverage** stays the system-health page: the 8-card summary and the budgets section. Layout unchanged (the owner likes it).
- **Catalogue** becomes the browsing page: it drops `CoverageSummary`, shows its own summary chips (total, per source, per pipeline stage) that act as clickable filters on the table below, and the table gains a Title column (truncated with the tooltip) and a stage filter. Layout unchanged.

The two pages no longer share a stats block, so the "same information at the top" complaint is resolved by distinction rather than a shared component with a flag.

## 10. Screenshot collection (chapter 1 and the live runs)

`capture_screenshot` (Cloudflare Browser Run, JPEG, 570 browser seconds a day, one request per 11 seconds, about 4 pages a minute) is queued by `llm_extract` only after mentions are posted (decision D13 of crawlers), is not in the default drain kinds, and can only be enqueued today by that handler. No machine route links a catalogue row to its mentions, so a repair tool cannot know which pages were categorised. Chapter 1 adds:

- a read-only machine route listing the catalogue rows that have at least one candidate mention and no screenshot, with the newest `html_snapshot` URL of each; and
- `capture requeue` in `apps/discovery-ingest` (`--host`, `--limit`, `--dry-run`, same shape as `llm requeue`), idempotent through the queue's identity (`shot@1`).

[02-live-runs.md](02-live-runs.md) then measures the queue, requeues, drains locally (GitHub Actions minutes are exhausted until about 2026-11-01) and verifies. Screenshots belong to procedures; the public screenshot of a candidate is the newest one among its procedures.

## 11. Budgets and exposure

- Public screenshot reads are R2 Class B reads. The proxy route counts each through the existing metered object store (the discovery router's override) and answers 503 over budget; immutable caching and ETag keep repeat views from reaching the store at all. List pages never include screenshot bytes or URLs, only the `has_screenshot` flag, so a page of 20 costs nothing.
- The candidates are **unreviewed model output** (the 2026-10-30 drain judged 10 to 17 of 58 names false positives). The owner chose to expose them all (D1); every public page carries a "staged, unreviewed" notice. A curation gate or kill switch is an open seam.

## 12. Showcase candidates (chapter 11 and live run LR2)

Production staging is sparse (domain codes on 6 of 58 candidates, no life-situation code, no screenshot on 2026-10-30), so the pages cannot be judged on live data. After the completeness model is deployed and the screenshots are collected, the chief of staff takes the **highest-ranking** candidates from the public list (`GET /api/v1/candidates`, completeness descending) and fills their missing flags by hand:

| Missing flag | How it is filled |
| --- | --- |
| `has_domain`, `has_situation` | A `manual` mention carrying codes from the closed taxonomy, chosen by reading the procedure page (the override of section 3). |
| `has_edges` | `manual` edges `parent requires required` with a verbatim excerpt from the page, checked against the cleaned page text; a missing neighbour becomes a `manual` candidate on the same procedure. |
| `has_snapshot` | Already true for any candidate extracted from a snapshot; a top candidate without one is skipped for the next in rank. |
| `has_screenshot` | The pages of the chosen candidates are captured first (`capture requeue --service-id ...`, then the drain). |

The set is chosen to exercise the interface, not to be representative: at least one candidate with ingress and egress, one with only ingress, one with only egress, one with many neighbours (the diagram cap), one with a long title (the tooltip), one whose tags cover both axes with two codes. The edits go through the validated, file-driven `candidates curate` command; the curation file is committed so the owner can review it, and everything written is marked `manual` so it is auditable and removable (reversal SQL in the operator doc). Nothing is emitted.

## 13. Out of scope

Emit, voting, moderation, editing or deleting extracted rows, translation of staged titles, a persisted completeness column or materialised view, a graph library, server-side screenshot thumbnails, search over mention text, authentication of the public pages, pagination of ingress or egress (a candidate has few), changes to extraction quality (the extraction suite's E21).
