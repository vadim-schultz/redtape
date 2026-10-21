---
name: PVOG v7 ingest — Gaps and decisions
overview: "Settled decisions for Lebenslagen tree walk, v7 response parsing, mapping, and GHA page budget."
isProject: false
---

# PVOG v7 ingest — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **No parameterless v7 list** — federal ingest must pass `personalMatters` (or `q`/LeiKa); scheduled path uses **Lebenslagen tree walk**, not a maintained static code list. |
| D2 | **Bootstrap seed** — `personalMatters=Geburt` with `facades=true` on first GET; constant in code, documented in canon. |
| D3 | **Leaf-only codes** — DFS collects `code` only for nodes without `children`; then `sorted` for deterministic iteration. |
| D4 | **Pagination** — read `serviceDescriptions.content`, advance `page` while `last` is false; ignore legacy top-level `next` for v7 (helper may still parse old fixtures in tests). |
| D5 | **`max_pages`** — counts every HTTP GET (bootstrap + all code pages); GHA keeps `--max-pages 50` until a follow-up raises it. |
| D6 | **Dedupe** — within one `pvog run`, skip rows with duplicate lb `id` across personalMatter queries. |
| D7 | **`external_id`** — `pvog:leika:{key}` when `leikakeys[0]` present; else `pvog:lb:{id}`; drop requirement for `portalId` + OD `id` pair. |
| D8 | **PR CI** — fixture-only PVOG; no live `pvog.fitko.net` in `./ci.sh` ([discovery-online-smoke D6](../discovery-online-smoke/gaps-and-decisions.md)). |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Raise GHA `--max-pages` or shard Lebenslagen | Partial ingest under 50 GETs; operator needs fuller `source=pvog` catalogue |
| `q` / LeiKa supplement crawl | Rows exist in PVOG but never under any leaf `personalMatters` code |
| HTML strip in `description_i18n` | Admin UI noise from v7 HTML descriptions |
| Bootstrap seed not full tree | Empty or single-branch facades — add ordered fallback seeds |
