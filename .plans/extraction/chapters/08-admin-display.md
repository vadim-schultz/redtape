---
name: "Chapter E8 — Admin display"
overview: "Show what extraction staged in the admin: conditions, optional flags and the issued role on mentions, suggested domain and life-situation chips with support counts, the edges of a document, llm_extract outcomes in Coverage, and a neuron meter."
todos:
  - id: api
    content: "Coverage counts of llm_extract by result note and the neuron figure in the admin budgets route"
    status: pending
  - id: detail
    content: "Mention columns, tag chips and edges panel on the document detail page"
    status: pending
  - id: coverage
    content: "Coverage chips and neuron meter"
    status: pending
isProject: false
---

# Chapter E8 — Admin display

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/extraction-admin-display` · **Status:** planned

**Depends on:** [E1](01-staging-groundwork.md), and crawlers [16](../../crawlers/chapters/16-admin-artifacts-panel.md), [20](../../crawlers/chapters/20-admin-document-detail-and-evidence.md), [23](../../crawlers/chapters/23-free-tier-guards.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

A reviewer must see, in one place, what the model claimed, what it quoted, how many procedures agree, and what depends on what, before anything is emitted. Everything is read-only (crawlers D16).

## Contract

**API.**

- The admin coverage response (crawlers chapter 14) gains `llm_extract` task counts by `result_note` prefix (`no_content`, `login_wall`, `no_documents`, `docs=…` grouped as `extracted`).
- `GET /admin/budgets` (crawlers chapter 23) already lists `neurons`; nothing new is needed beyond the resource being populated by chapter E4.
- Candidate detail and `/edges` come from [E1](01-staging-groundwork.md).

**Web** (`apps/web/src/features/discovery-admin/`, the document page from crawlers chapter 20):

- the mentions table adds a `condition` cell, an optional chip, and the `issued` role chip (role chip component shared with the list);
- `components/DocumentTagsPanel.tsx`: suggested domain and life-situation chips using the same chip look as the public front page, each with its support, for example "Wohnen · 3 of 4 procedures", with an `accepted` style for codes that pass the thresholds and a muted style for the rest; an empty state "no consensus yet";
- `components/DocumentEdgesPanel.tsx`: lists "requires" edges (the other document's title linking to its detail page, condition, optional chip, basis chip `explicit` or `derived`, and the procedure link) and the reverse "required by" list;
- `hooks/useCandidateEdgesQuery.ts` for `/edges`, owned by the container like the other queries;
- Coverage: an `llm_extract` chip row (extracted, no documents, login wall, no content) and a neuron meter (used of cap today) from the budgets route, using the same meter component as crawlers chapter 16;
- the Tasks table shows `llm_extract` in its kind select and the note as a chip (raw value fallback already exists);
- strings under `discovery_admin.document.tags.*`, `discovery_admin.document.edges.*` and `discovery_admin.coverage.llm.*` in `apps/web/src/i18n/fallback/{de,en}.json`;
- **no emit control** (crawlers chapter 20's absence test stays green).

## TDD loops

### Loop A — API

**Red** (`test_discovery_coverage.py`)

1. `coverage groups llm_extract tasks by result note and reports zeros when there are none`.
2. `coverage requires an admin`.

**Green:** extend the grouped query. **Refactor:** reuse the existing grouped-count helper.

### Loop B — Web

**Red** (Vitest, beside the document page tests)

1. `mentions table shows condition, the optional chip and the issued role`.
2. `tags panel shows suggested chips with support counts, styles accepted codes differently, and shows the empty state`.
3. `edges panel shows requires and required-by with condition, basis and procedure links, and an empty state`.
4. `coverage shows the llm_extract outcome chips and the neuron meter with used and cap`.
5. `all new strings resolve in German and English` — the existing i18n fallback test pattern.
6. `the document page still has no emit control`.

**Green:** container → hooks → presentational components; keep each file about a hundred lines. **Refactor:** the chip component is shared with the Documents list.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_coverage.py
cd apps/web && npm run test -- src/features/discovery-admin && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: as an allowlisted admin, open a candidate produced by the E7 live run: mentions with conditions, tag chips with support, edges both ways, Coverage with the `llm_extract` row and the neuron meter. Check the layout at phone width. Record the candidate id.

## Out of scope

Editing, merging or deleting staged items, an emit button, voting controls, a graph visualisation of edges, per-document tag editing.
