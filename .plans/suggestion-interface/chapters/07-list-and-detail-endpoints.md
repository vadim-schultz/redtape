---
name: "Chapter 7 — List and detail endpoints"
overview: "Public GET /api/v1/suggestions with status, kind, source and jurisdiction filters and pagination, and GET /api/v1/suggestions/{id}; submitter shown by display name only."
todos:
  - id: repo
    content: "Filtered, paginated list and count"
    status: completed
  - id: routes
    content: "Controller list and detail handlers"
    status: completed
isProject: false
---

# Chapter 7 — List and detail endpoints

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-read` · **Status:** implemented, PR open

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

## Progress

All 16 red tests in `test_suggestions_read.py` pass alongside the full suite (280 tests). Implementation
followed the planned Green order (unfiltered list → one filter at a time → limits/joined submitter →
detail), landed as the two commits below rather than one per slice, since each slice was small enough to
stay reviewable together.

`SuggestionRepository._apply(stmt, *, status, kind, source_type, jurisdiction_id)` matches the refactor gate
almost verbatim: it iterates a tuple of `(values, column)` pairs and applies `column.in_(values)` for each
non-empty one — no if-chain, and adding a filter is one more tuple entry. `status` is the only filter that's
inherently a sequence (`?status=pending&status=approved`); `kind`/`source_type`/`jurisdiction_id` are wrapped
into a single-element tuple when present so they flow through the same loop.

Submitter display name is resolved with `func.coalesce(AppUser.display_name, ApiKey.name)` over two
`outerjoin`s in `SuggestionRepository._with_submitter()`, reused by both `list_page` and the new
`get_with_submitter`. Coalesce is safe here (not just convenient) because the `ck_suggestion_submitter_matches_source`
check constraint guarantees at most one of `submitted_by_user_id`/`submitted_by_api_key_id` is set per row, so
at most one join ever produces a non-null value. This keeps list and detail at one query each regardless of
row count — the N+1 guard test asserts equal query counts at 3 and 13 rows via a `before_cursor_execute`
listener on the test's own connection.

Controller handlers stayed small: `list_suggestions` builds a `SuggestionFilters` from query params and
delegates (3 lines); `get_suggestion` delegates and 404s on `None` (4 lines) — both within the ≈5 LOC target.

One deviation from the chapter as planned: `SuggestionRepository.count`/`list_page` take the four filter
values as individual keyword arguments rather than a single `SuggestionFilters` object, even though `_apply`
reads as if it took one. Mirroring `DocumentRepository` (which takes `jurisdiction_id`/`domain_ids`/
`situation_ids` directly, not a `DocumentFilters`) keeps the repository from importing a dataclass owned by
the service layer, preserving the repos → services → controllers layering. `SuggestionService.list_suggestions`
unpacks `SuggestionFilters` into named keyword arguments at the call site (not `**scope`, unlike
`DocumentService`) because mypy checks a `**dict[str, UnionOfAllFieldTypes]` unpack against every keyword
parameter's own type individually, which fails whenever the fields have genuinely different types (here:
`Sequence[SuggestionStatus] | SuggestionKind | SuggestionSource | UUID | None` isn't assignable to each
parameter on its own, even though each individual key matches its parameter). `DocumentService`'s equivalent
`**scope` unpack happens to pass only because two of its three fields share the same `Sequence[UUID]` type;
the general case needs named arguments.

`test_malformed_id_returns_404_or_422` in the chapter's red-test table was written and observed directly:
Litestar's `{suggestion_id:uuid}` path type fails to match a non-UUID segment, so the route itself doesn't
match and the request 404s (never reaching a 422 from body/param validation). The test was named
`test_malformed_id_returns_404` to state the observed behavior rather than the either/or.

`./ci.sh` is green: apps/api pytest — 280 passed; ruff format/check and mypy clean; migrations round trip
clean; web lint/format/typecheck/test/build all pass. Manual verification: `GET /api/v1/suggestions?status=pending&limit=5`
against a running server returns `{"items":[],"total":0,"offset":0,"limit":5}` with `Cache-Control: no-cache`.

Commits on `feat/suggestions-read`:
1. `test(api): describe listing, filtering and reading suggestions`
2. `feat(api): add suggestion list and detail endpoints`

PR opened against `main`.

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
