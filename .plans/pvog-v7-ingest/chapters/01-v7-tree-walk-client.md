---
name: "Chapter 1 — v7 tree walk client"
overview: "PvogClient: facades bootstrap, deterministic leaf personalMatter codes, serviceDescriptions pagination, dedupe, max_pages budget."
todos:
  - id: fixtures
    content: "facades_personal_matters.json + v7_page_*.json fixtures"
    status: pending
  - id: tree
    content: "_personal_matter_codes_from_facades leaf-only sorted"
    status: pending
  - id: client
    content: "iter_records v7 URLs + global max_pages"
    status: pending
isProject: false
---

# Chapter 1 — v7 tree walk client

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/pvog-v7-tree-walk-client` · **Status:** planned

**Depends on:** none · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-pvog-v7-ingest`

---

## Goal

Replace bare `GET /v7/servicedescriptions/{ars}` with a **deterministic Lebenslagen tree walk**: bootstrap facades → sorted leaf codes → paginated search per code → yield deduped rows.

## Design decisions

Per [../gaps-and-decisions.md](../gaps-and-decisions.md) D1–D6.

| Constant | Value |
| --- | --- |
| Federal ARS | `000000000000` |
| Bootstrap seed | `personalMatters=Geburt`, `facades=true` |
| Page size | `100` (≥ OpenAPI minimum `5`) |

## Files

| Path | Change |
| --- | --- |
| [`apps/discovery-ingest/discovery_ingest/pvog/client.py`](../../../apps/discovery-ingest/discovery_ingest/pvog/client.py) | v7 URL builder, tree walk, pagination, dedupe |
| [`apps/discovery-ingest/tests/fixtures/pvog/facades_personal_matters.json`](../../../apps/discovery-ingest/tests/fixtures/pvog/facades_personal_matters.json) | Bootstrap tree |
| [`apps/discovery-ingest/tests/fixtures/pvog/v7_page_*.json`](../../../apps/discovery-ingest/tests/fixtures/pvog/) | Wrapped `serviceDescriptions` pages |
| [`apps/discovery-ingest/tests/test_pvog_client.py`](../../../apps/discovery-ingest/tests/test_pvog_client.py) | Tree + pagination tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_personal_matter_codes_from_facades_leaf_only_sorted` | Parent with `children` excluded; output sorted |
| `test_personal_matter_codes_from_facades_empty_tree` | Empty / missing facades → `[]` or explicit error at fetch layer |
| `test_v7_page_extracts_service_descriptions_content` | Parser reads `serviceDescriptions.content` |
| `test_v7_page_missing_service_descriptions_returns_empty` | Missing wrapper → no records |
| `test_pvog_client_iterates_personal_matter_codes_with_dedupe` | Two codes, same `id` once |
| `test_pvog_client_stops_at_max_pages_budget` | Global GET cap honored |

## Refactor gate

Audit `PvogClient` and new helpers (`_personal_matter_codes_from_facades`, `_parse_v7_page`, `_build_v7_url`); extract if branch count > 2 per decision; report outcome.

## Verification

```bash
cd apps/discovery-ingest && uv run pytest tests/test_pvog_client.py -q
```

## PR

Target loop branch only.
