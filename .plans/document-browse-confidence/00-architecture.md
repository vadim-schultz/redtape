---
name: Document browse by confidence — Architecture
overview: "situation-tag-hierarchy turned every tag decision into a continuous confidence score, which makes 'emit and publish a document' moot. This suite makes the discovered candidate pool the one document list: every document is searchable and sortable, chips filter by presence regardless of confidence, and confidence is shown as a traffic-light ProgressCircle. It also adds two-stage swiss-red life-situation chips, fixes the menu (centred Home, close on select), unlinks the suggestion UI, and removes the seeded documents."
isProject: false
---

# Document browse by confidence — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Prior suites:** [situation-tag-hierarchy](../situation-tag-hierarchy/00-architecture.md) (continuous confidence, group tier) → [candidate-view](../candidate-view/00-architecture.md) (public candidate list) → [frontend-ui-menu](../frontend-ui-menu/00-architecture.md) (the menu)

## 1. Why

`situation-tag-hierarchy` removed every accept/reject boolean from tagging: a code now has a score in `[0, 1]`, and nothing downstream asks "accepted or not". The visibility gate that remains is a leftover of the old model: a discovered document only appears on `https://redtape.cc/documents` after it is **emitted** as a suggestion, **voted** to +3 and **promoted** into the `document` table. With confidence on every tag, that pipeline protects nothing — it only hides almost the whole catalogue.

Today there are two disjoint lists (confirmed by reading the code, 2026-11-02):

| Surface | Source | What it shows | What it lacks |
| --- | --- | --- | --- |
| `/documents` | `GET /api/v1/documents` → `document` rows | The 4 seeded MVP documents plus anything promoted by +3 votes | `q`, sort, confidence on list items; shows the first 20 only |
| `/candidates` | `GET /api/v1/candidates` → `discovery_document_candidate` | Every staged or emitted candidate, ranked by completeness | confidence values; its chip filter only matches codes above the 0.05 inclusion floor; one code per axis |

This suite makes the candidate pool the single list behind `/documents`, and gives it the browsing tools the user asked for.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Document** | In the UI, a discovered candidate. The word on screen stays "document"; the data is a `discovery_document_candidate` row. |
| **Tag score** | The continuous score of one `(candidate, axis, code)` — the output of the existing scorer (`candidate_axis_support`), now also computed in SQL for the whole pool. |
| **Score model** | The SQL relation `candidate_tag_scores(candidate_id, axis, code, score)`. Single definition used by the filter, the sort and the displayed value. |
| **Card confidence** | The document's single number shown in the circle: the **max** tag score among the tags in the current filter (the selected domain and situation codes), or the max over all of its tags when no chip is selected. |
| **Band** | `low` (`< 0.4`), `mid` (`0.4 … < 0.7`), `high` (`>= 0.7`). Constants live in one module. |
| **Group-wide selection** | A top-level life area (one of 8 groups) is selected: matches every document tagged with **any** situation of that group. |
| **Sub selection** | One or more situations inside a group are selected: finer than the group. |
| **Dormant** | Left in the code and database but unreachable from the UI: the suggestion form, emit/vote/promote, `GET /api/v1/documents`, `GET /api/v1/matrix`, web `/documents/:id`. |

## 3. API contract (`GET /api/v1/candidates`)

Existing: `q` (title, any locale, case-insensitive, no index), `sort_by`, `sort_order`, `filter[...]`, `offset`, `limit` (1–100) through the shared list-query parser (`apps/api/app/shared/list_query/`). Changes:

| Parameter | Today | After this suite |
| --- | --- | --- |
| `filter[domain]` | one code, must be an **accepted** code | CSV of 1–20 codes (`a,b,c`); a candidate matches when it carries **any** of them with **any** score |
| `filter[situation]` | same | same CSV rule |
| across axes | AND | AND (unchanged) |
| `sort_by` | `completeness \| mentions \| title \| created_at` | adds `confidence` |
| default order (no `sort_by`) | completeness desc, mentions desc | confidence desc, then completeness desc, mentions desc, deterministic tie-break |
| unknown code | 422 | 422, per code |
| `filter[complete]` | `yes \| no` | unchanged (kept for the API; the new UI does not expose it) |

`CandidateTag` gains `confidence: float`. `CandidateCard` gains `confidence: float` (card confidence, §2). The card's `domains` and `situations` list **every** code with a score, most confident first — not only the accepted ones. The completeness flags (`has_domain`, `has_situation`, `complete`) keep using the accepted-code rule; see [gaps-and-decisions.md](gaps-and-decisions.md) seam S2.

The score model mirrors the Python scorer exactly: a manual mention replaces the consensus for its axis at score `1.0`; otherwise the LLM evidence curve (`LLM_SCORE_BASE`, `LLM_SCORE_STEP`, `LLM_SCORE_CEILING` in `app/features/discovery/tags.py`) and any direct source confidence (PVOG) are combined by noisy-OR. **There is no inclusion floor on this path**; `MIN_SUGGESTED_SCORE` (0.05) remains in force only for the dormant emit payload.

## 4. Web contract

URL (friendly, repeated params; the service layer maps them to the API's CSV filters):

`/documents?domain=housing&domain=work&group=family-relationships&situation=moving-house&q=ausweis&sort_by=confidence&sort_order=desc&offset=20`

- `group` and `situation` are mutually exclusive **per group**: selecting a group clears that group's selected situations; selecting a situation removes its group from `group`.
- The request's `filter[situation]` is `union(codes of selected groups, selected situations)`; groups are expanded in the web from the already-loaded taxonomy (`GroupedTerm.group_code`). No API change.
- Search is submit-applied (as on `/candidates` today). Sort exposes three keys: confidence, title, newest (`created_at`), each asc/desc. Any filter/search/sort change resets `offset`.
- Cards link to `/candidates/:id` (the existing item page with flow diagram); `/candidates` redirects to `/documents`.

## 5. Colour contract

| Use | Token |
| --- | --- |
| Domain chip, selected | unchanged: `colorPalette="primary"`, `variant="solid"` (primary.500, swiss red `#DA291C`) |
| Life-area (group) chip, selected | swiss red, `primary.500` solid — the same red as every other selected chip |
| Life-situation (sub) chip, selected | a lighter red: new semantic tokens, a tone between `primary.100` and `primary.300`, with a foreground that passes WCAG AA (asserted in `theme/theme.test.ts`) |
| Group chip, only sub-selections inside it | outline variant in primary — a hint that the filter inside is narrower |
| Confidence circle | stock Chakra `red`, `yellow`, `green` palettes (not brand `primary`, so a low-confidence ring is distinguishable from a selected chip): the whole ring in the band colour — `Track` = `colorPalette.muted`, `Range` = `colorPalette.solid` (the darker sector is the value), `ValueText` shows the percentage |

Chakra `ProgressCircle` (installed `@chakra-ui/react` 3.37.0) exports `Root / Circle / Track / Range / ValueText`; it is not used anywhere in the app yet.

## 6. Menu behaviour

| Item | Closes the menu? |
| --- | --- |
| Home, profile (`/login` links), Documents row links, discovery admin links | yes |
| Sign out | yes |
| Language flag | yes (already) |
| Colour mode switch | no (frontend-ui-menu D4) |

Root cause of the open menu: the links are plain elements, not Chakra `Menu.Item`s, so Ark's `closeOnSelect` never fires, and `AppMenu` is mounted once above the router outlet, so its `open` state survives navigation. Fix: one delegated `onClick` on `Menu.Content` that closes on a click inside `a[href]` or the sign-out button. Home is centred (`HomeMenuButton`, `justifyContent="center"`).

## 7. What stays dormant, and why

The suggestion API, voting, events, `new_requirement` handling, discovery emit (`/machine/candidates/emit`, `DocumentEmitPanel`) and the `document` table with its API stay untouched. Removing them is a separate, larger decision (it would drop user-submitted requirement edges and 25+ tests). Docs mark them dormant in chapter 10.

## 8. Seeded documents

`scripts/seed_documents.py` upserts the DE/SN/DD jurisdictions, 4 sample documents and 3 requirements, and `scripts/start.sh` re-runs it on every boot. This suite stops seeding the documents and requirements, deletes those exact rows with a data migration, and keeps the jurisdictions and the taxonomy. Real data comes from the database (candidates).
