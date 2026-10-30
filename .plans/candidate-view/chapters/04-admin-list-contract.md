---
name: "Chapter 4 — Admin list contract"
overview: "Give the admin candidate list a sort key and filter for every column the table will show, plus the completeness flags in each row, on the same read model as the public list, keeping the legacy parameters working."
todos:
  - id: spec
    content: "Extend the candidate list-query spec with the new sort keys and filters"
    status: pending
  - id: sorting-filtering
    content: "Sort and filter expressions for jurisdiction, status, roles, completeness and the flag filters"
    status: pending
  - id: response
    content: "Flags and completeness on CandidateListItemRead"
    status: pending
isProject: false
---

# Chapter 4 — Admin list contract

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/candidate-view-admin-list-contract` · **Status:** planned  
**Depends on:** [02-completeness-read-model.md](02-completeness-read-model.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 8) · **Decisions:** D8, D11 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

`GET /api/v1/discovery/admin/candidates/` sorts on `mentions`, `title` and `created_at` only and filters on `status`, `role`, `source` and `min_mentions`. The documents table of chapter 8 wants **every column** sortable and filterable and a Readiness column that answers "which candidates are ready" (decision D8). This chapter widens the contract and the response; it changes no screen.

## Contract

Spec in [`candidate_list_query.py`](../../../apps/api/app/features/discovery/candidate_list_query.py) (l.11-19); sort keys in `repository/candidate_sort.py:17-22` (`CandidateSortKey`); filters in `repository/candidate_filter.py`; listing in `repository/candidate_listing.py:61-80`.

| New sort key | Order |
| --- | --- |
| `jurisdiction` | The jurisdiction name resolved like the title expression (`de`, else `en`, else key), case-insensitive. |
| `status` | The enum's declared order (`staged`, `emitted`). |
| `roles` | Number of distinct roles among the mentions, then the stats subquery's role array text, so rows sharing a role set group together. |
| `completeness` | The read model's `completeness` (chapter 2). |

Existing keys `mentions`, `title`, `created_at` are unchanged. Ordering stays deterministic: the requested key and direction, then the existing tail (`title_expression()` ascending, `Candidate.key`, `Candidate.id`, `candidate_sort.py:53-57`).

| New filter | Rule |
| --- | --- |
| `filter[complete]` | `yes` or `no` (the read model's `complete`). |
| `filter[has_domain]`, `filter[has_situation]`, `filter[has_edges]`, `filter[has_snapshot]`, `filter[has_screenshot]` | `yes` or `no` each. |
| `filter[jurisdiction]` | A jurisdiction id (UUID); an unknown id returns an empty page, a non-UUID is a 422. |
| `filter[domain]`, `filter[situation]` | A taxonomy code that must be **accepted** for the candidate; unknown code 422 (same resolver as chapter 3). |
| `filter[min_mentions]` | Becomes usable from the header as a `gte` filter on Mentions; semantics unchanged (integer at least 0). |

Existing filters `status`, `role`, `source`, `min_mentions` and the **legacy parameters** (`status`, `role`, `source`, `min_mentions`, `sort`) keep working; canonical parameters win over legacy ones exactly as today (`candidate_list_query.py:22-34`). `q` is unchanged. The machine list (`GET /machine/candidates/`, `candidate_machine_controller.py:49`) keeps its `status` and `min_mentions` only and is not widened.

Response: `CandidateListItemRead` ([`schema/discovery/read.py:262-266`](../../../apps/api/app/schema/discovery/read.py)) gains `completeness: int`, `complete: bool` and `flags: CandidateFlags` (`has_domain`, `has_situation`, `has_edges`, `has_snapshot`, `has_screenshot`). The fields are always present (additive change; the web type is updated in chapter 8). `total` still counts the full filtered result.

Everything is behind the unchanged `DISCOVERY_ADMIN_GUARDS`.

## Red tests

Extend `apps/api/tests/test_discovery_admin_list_query.py` patterns (sort both directions, tie determinism across pages, total consistent with filter, literal `q`, legacy-versus-canonical precedence, 422 on bad params) in a new `apps/api/tests/test_discovery_candidates_list_contract.py` using `_admin_headers()` and the shared admin `client` fixture.

| Test | Asserts |
| --- | --- |
| `candidate list sorts by jurisdiction both ways` | Three jurisdictions: ascending and descending name order; ties stable. |
| `candidate list sorts by status` | `staged` before `emitted` ascending; reversed descending. |
| `candidate list sorts by roles` | Candidates with one role precede those with two ascending. |
| `candidate list sorts by completeness` | Order matches the flags count; ties by the deterministic tail. |
| `candidate list pages deterministically on every new key` | For each new key, `limit=1` pages cover all rows exactly once. |
| `candidate list filters by complete and each flag` | `filter[complete]=yes`, `filter[has_screenshot]=no`, etc. return the expected rows; `total` equals the filtered count. |
| `candidate list filters by jurisdiction` | Id match returns its rows; unknown id empty; negative: non-UUID 422. |
| `candidate list filters by an accepted domain code` | A code supported by one procedure only is excluded; an accepted one is included; negative: unknown code 422. |
| `candidate list rejects an invalid flag value` | Negative: `filter[complete]=maybe` is 422 with the shared validation shape. |
| `candidate list rejects an unknown sort key` | Negative: `sort_by=roles2` is 422 and runs no query. |
| `legacy parameters still work` | `?status=staged&min_mentions=2&sort=-mentions` unchanged results; a canonical `filter[status]=emitted` wins over legacy `status=staged`. |
| `candidate list rows carry the completeness flags` | Items include `completeness`, `complete` and the five flags, equal to chapter 2's read model for the same candidates. |
| `candidate list stays admin only` | Negative: no token 401, a non-allowlisted token 403, discovery disabled 503, as today. |
| `machine candidate list is unchanged` | `GET /machine/candidates/` accepts only its two filters and returns rows without the new fields requirement failing (pin its current shape). |

Write and run these before implementing.

## Green

1. Extend `CandidateSortKey` and the `CandidateListQuerySpec` sort set; add enum filters for the flags (`enum_filter`), a UUID filter for `jurisdiction`, taxonomy-code filters.
2. Add sort expressions to `candidate_sort.py` (one small function per key, table-driven mapping instead of an `if` chain) and filter conditions to `candidate_filter.py`, joining the chapter 2 subquery only when a completeness sort or flag filter is requested (otherwise the existing query is untouched, so the old path costs nothing).
3. Extend `candidate_listing.py` to select the completeness columns for the page of rows and map them into `CandidateListItemRead` / `CandidateFlags`.
4. Keep `candidate_list_query.py` legacy mapping; add the new keys to its canonical side only.

## Files

**Edit**

- `apps/api/app/features/discovery/candidate_list_query.py`
- `apps/api/app/features/discovery/repository/candidate_sort.py`, `candidate_filter.py`, `candidate_listing.py`
- `apps/api/app/schema/discovery/read.py` (flags and fields)
- `apps/api/tests/test_discovery_candidates_list_contract.py` (new)
- `apps/api/tests/test_discovery_candidates_admin_api.py` only if an existing response assertion needs the new fields

**Do not edit**

- The admin guards, the machine controller, the public candidates package (chapter 3), models, migrations
- The completeness query itself (chapter 2); if it needs a change, fix it in a follow-up on chapter 2's module and say so in the PR

## Refactor gate

Audit `candidate_sort.py`, `candidate_filter.py` and `candidate_listing.py`: each function about 5 lines, one nesting level, files about 100 lines (split `candidate_filter.py` into `candidate_filter_flags.py` if it grows), the sort key to expression mapping table-driven, no `Any`, docstrings on new public items, and no copy of the public list's ordering code (rule of three: if three lists now share the same tail ordering, extract it once). Report the outcome.

## Verification

```bash
cd apps/api && pytest tests/test_discovery_candidates_list_contract.py tests/test_discovery_admin_list_query.py tests/test_discovery_candidates_admin_api.py tests/test_candidate_completeness.py tests/test_discovery_candidates_api.py
cd ../.. && ./ci.sh
```

## Commits

`test(api): define the admin candidate sort keys and filters`, `feat(api): widen the admin candidate list contract`, `refactor(api): table-drive the candidate sort expressions`.

## Out of scope

Any web change (chapter 8), the public list (chapter 3), the machine list, free-text search over mentions, a saved-filter feature, changing the status enum or the guards.
