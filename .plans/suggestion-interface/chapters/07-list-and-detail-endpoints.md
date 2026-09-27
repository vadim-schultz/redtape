---
name: "Chapter 7 — List and detail endpoints"
overview: "Public GET /api/v1/suggestions with status, kind, source and jurisdiction filters and pagination, and GET /api/v1/suggestions/{id}; submitter shown by display name only."
todos:
  - id: repo
    content: "Filtered, paginated list and count"
    status: pending
  - id: routes
    content: "Controller list and detail handlers"
    status: pending
isProject: false
---

# Chapter 7 — List and detail endpoints

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-read` · **Status:** planned

**Depends on:** [3](03-suggestion-repository-service.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Anyone can browse suggestions (D7): the pending queue people vote on, and the history of approved and
rejected ones.

## Design decisions

**Mirror the documents list** ([controller.py](../../../apps/api/app/features/documents/controller.py)): a
`SuggestionFilters` frozen dataclass in the service (`status`, `kind`, `source_type`, `jurisdiction_id`),
`offset`/`limit` with `limit` 1–100 default 20, response `{items, total, offset, limit}` reusing the
documents pagination shape.

**Ordering**: newest first (`created_at DESC, id DESC` for stable pages). Default filter is **no status
filter** (all), the web passes `status=pending` for the voting agenda.

**Enum filters validated by Litestar** through the enum types, so `?status=bogus` is a 422 without custom
code. Multiple values (`status=pending&status=approved`) are supported as a list.

**Submitter display**: the repository loads the user or key with a single joined query (no N+1) and the
read model exposes `{kind, display_name}`; key `name` for crawlers (for example `crawler-de-federal`), user
`display_name` or `null`. Email and key hash are never selected.

**Detail 404** uses the same `NotFoundException` pattern as documents. No auth; caching is
`Cache-Control: no-cache` (state changes with votes) to avoid stale queues.

**Dispatch table not needed yet**: kinds render through the same `SuggestionRead`; payload is returned as
stored.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/repository.py` | `list_page`, `count` with filters and joined submitter |
| `apps/api/app/features/suggestions/service.py` | `SuggestionFilters`, `list_suggestions`, `get_suggestion` |
| `apps/api/app/schema/suggestion/read.py` | `SuggestionListResponse` |
| `apps/api/app/features/suggestions/controller.py` | `GET /`, `GET /{id}` |
| `apps/api/tests/test_suggestions_read.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `GET /suggestions · lists newest first` | Order by `created_at` |
| `GET /suggestions · paginates with total, offset and limit` | Second page, total unchanged |
| `GET /suggestions · filters by status` | Only pending |
| `GET /suggestions · accepts several statuses` | Union |
| `GET /suggestions · filters by kind` | New-document only |
| `GET /suggestions · filters by source_type` | Crawler only |
| `GET /suggestions · filters by jurisdiction_id` | Other jurisdictions excluded |
| `GET /suggestions · rejects an unknown status with 422` | Negative |
| `GET /suggestions · rejects limit 0 and 101` | Boundaries |
| `GET /suggestions · needs no authentication` | 200 anonymous |
| `GET /suggestions · never exposes emails or key hashes` | String search over the whole body |
| `GET /suggestions · lists with a constant number of queries` | Query count does not grow with rows (N+1 guard) |
| `GET /suggestions/{id} · returns the suggestion` | Detail |
| `GET /suggestions/{id} · unknown id returns 404` | Negative |
| `GET /suggestions/{id} · malformed id returns 404 or 422` | Litestar path type behaviour, asserted as observed |

## Green

1. Repository list/count unfiltered; ordering and pagination; tests 1–2.
2. One filter at a time; tests 3–8.
3. Limits; joined submitter; tests 9–12.
4. Detail; tests 13–15.

## Refactor gate

- Filter application is one function `_apply(stmt, filters)` with one line per filter (dispatch by a list of
  `(value, column)` pairs, not an if-chain).
- Controller handlers ≈5 LOC. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestions_read.py
cd ../.. && ./ci.sh
curl -s 'localhost:8000/api/v1/suggestions?status=pending&limit=5'
```

## Out of scope

Vote counts and `my_vote` in the response (voting suite chapter 4), full-text search, evidence links.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-read
```

```text
test(api): describe listing, filtering and reading suggestions

feat(api): add suggestion list and detail endpoints
```
