---
name: "Chapter 3 — Public candidate API"
overview: "An unguarded, read-only candidates package: a ranked list, an item with ingress, egress, tags, sources and screenshot reference, and a cached screenshot proxy that answers 304 and 503 over the R2 read budget."
todos:
  - id: schema
    content: "CandidateCard, CandidateDetail, CandidateNeighbour, CandidateSource DTOs under schema/candidate"
    status: pending
  - id: list-and-detail
    content: "GET /api/v1/candidates and /{id} on the completeness read model with the shared list-query contract"
    status: pending
  - id: screenshot
    content: "GET /api/v1/candidates/{id}/screenshot streaming proxy with immutable cache headers, ETag and 304"
    status: pending
  - id: wiring
    content: "Router registered in app/main.py with the metered object store and domain-error handlers"
    status: pending
isProject: false
---

# Chapter 3 — Public candidate API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/candidate-view-public-api` · **Status:** planned  
**Depends on:** [02-completeness-read-model.md](02-completeness-read-model.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 4) · **Decisions:** D1 to D5, D7, D9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

There is no public way to read a staged candidate. This chapter adds three unguarded read routes (a public route is a controller without `guards`, as `DocumentsController` is) on the completeness read model, plus a screenshot proxy that browsers and a CDN can cache.

## Contract

New package `apps/api/app/features/candidates/` (`router.py`, `controller.py`, `dependencies.py`, `service.py`, `list_query.py`, `repository.py`/split modules) and DTOs in `apps/api/app/schema/candidate/` (`read.py`). Router path `/api/v1/candidates`, registered in `app/main.py:25-47` next to `documents_router`. It **reuses** the discovery models, the composed discovery repository ([`composite.py`](../../../apps/api/app/features/discovery/repository/composite.py)) and the object store; it adds no table and no migration. Put the guards-free controller on its own `Router` (not on `discovery_admin_router`), but wire the **metered** object store and the discovery domain-error handlers (`router.py:62-70`) onto it: the discovery router's `object_store` override (`dependencies.py:100-103,131`) is what charges the R2 read ledger.

### `GET /api/v1/candidates`

Shared list-query contract (`shared/list_query/`: `ListQuerySpec`, `provide_list_query`, `enum_filter`; pattern of `candidate_list_query.py`):

| Parameter | Rule |
| --- | --- |
| `sort_by` | `completeness` (default), `title`, `mentions`, `created_at`. `sort_order` requires `sort_by`. Default order: `completeness desc, mentions desc`, then the deterministic tie-break of `candidate_sort.py:53-57` (title expression, `key`, `id`). |
| `filter[complete]` | `yes` or `no` (enum filter). |
| `filter[domain]`, `filter[situation]` | One taxonomy code each; the candidate must have that code **accepted** (from the read model). Unknown code: 422 with the standard validation shape (resolved with `TaxonomyService.known_domain_codes`/`known_situation_codes`, `features/taxonomy/service.py:41-47`; `TaxonomyCodeError` mapped like in `DocumentsController`). |
| `q` | 1 to 200 characters, case-insensitive contains over any locale of the title (reuse `repository/candidate_filter.py:32-35`). |
| `offset`, `limit` | `PageParams` (limit 1 to 100, default 20). |

Response `CandidateListResponse` `{items: CandidateCard[], total, offset, limit}`; `total` counts the full filtered result. `CandidateCard`:

| Field | Meaning |
| --- | --- |
| `id`, `key` | Candidate id and slug key. |
| `title` | Localized string via `app/i18n_resolution.py` (`ResolvedLocale`: requested, `de`, `en`, any). |
| `description`, `description_source` | Decision D4: excerpt of the first mention ordered by role (`required`, `form`, `issued`), then `created_at`, then `id`, cut to 300 characters; `description_source` is the localized title of that mention's procedure. Both `null` when the candidate has no mention (cannot happen for listed candidates, but the DTO allows it). |
| `status` | `staged` or `emitted`. |
| `domains`, `situations` | Accepted codes only, each `{code, name}` with the localized taxonomy name. |
| `completeness`, `complete`, `flags` | `completeness` 0 to 5; `flags` = `{has_domain, has_situation, has_edges, has_snapshot, has_screenshot}`. |
| `mention_count` | Mentions. |

The description is picked in SQL (`DISTINCT ON (candidate_id)` over mentions with the role rank) for the page of ids only, never for the whole table.

### `GET /api/v1/candidates/{id}`

`CandidateDetail` extends `CandidateCard` with:

- `ingress: CandidateNeighbour[]` (decision D2): edges where this candidate is the **parent** (it requires them); the neighbour is the `required` candidate.
- `egress: CandidateNeighbour[]`: edges where this candidate is the **required** end; the neighbour is the `parent`.
- `CandidateNeighbour`: `id`, `title`, `description`, `condition`, `is_optional`, `excerpt` (the edge's evidence quote), `basis` (`explicit` or `derived_single_issued`), `procedure_title`. Duplicate edges to the same neighbour (one per procedure) are merged into one neighbour: `condition`, `excerpt` and `procedure_title` come from the oldest edge, `is_optional` is true only if every merged edge is optional. Order: neighbour title, then id. At most 50 neighbours per side (a hard cap with `truncated` booleans `ingress_truncated`, `egress_truncated`).
- `sources: CandidateSource[]`: one per mentioning procedure, `{procedure_title, portal_url, role, excerpt, condition, is_optional}`; `portal_url` is exposed only when it is an `http` or `https` URL (a `javascript:` or `data:` value is returned as `null`).
- `screenshot: {url, fetched_at} | null`: `url` is the **relative** public proxy path `/api/v1/candidates/{id}/screenshot`, `fetched_at` of the newest screenshot; `null` when there is none. Never a presigned URL (decision D3).

`GET` with an unknown id: 404 `Candidate not found` (domain error `DiscoveryNotFoundError` mapped by the discovery handlers, or a local error mapped the same way).

### `GET /api/v1/candidates/{id}/screenshot`

- The newest `screenshot` artifact among the candidate's mentioning procedures (`fetched_at desc, id desc`), content read through the metered object store (`store.get(key)` or the streaming read the port offers; see `shared/object_store/port.py`).
- Response: body bytes, `Content-Type` as stored (`image/jpeg` or `image/png`), `Cache-Control: public, max-age=31536000, immutable`, `ETag: "<sha256>"` (the artifact is content-addressed: key `discovery/{catalogue_id}/screenshot/{sha256}.{ext}`).
- `If-None-Match` equal to the ETag: **304** with the same `ETag` and `Cache-Control`, **without reading the object store and without charging the ledger**.
- 404 when the candidate does not exist or has no screenshot (distinct messages). 503 (existing storage/budget domain errors) when the object store is not configured or the R2 read budget is spent; the error must be raised **before** any bytes are returned.
- Each 200 counts one R2 Class B read in the ledger (`artifact_read.py:97-100` behaviour through the same metered store).

No route here writes. No mention internals (`extractor`, `extractor_version`, `artifact_id`, `catalogue_service_id`) leave the API.

## Red tests

New file `apps/api/tests/test_candidates_public_api.py` following the standalone client pattern of `tests/test_documents_filter.py:39-67`: a local `client` fixture with `monkeypatch.setattr("app.main.provide_session", lambda: db_session)` and `TestClient(create_app())`, **no auth patches and no token** (the test itself proves the routes are public). Taxonomy via `seed_taxonomy(db_session, tags={})`. The screenshot tests swap the object store with `InMemoryObjectStore` through the dependency patch target of the discovery dependencies module (pattern `test_discovery_artifacts_api.py:32-78`, `StoreSlot`).

| Test | Asserts |
| --- | --- |
| `candidates list is public and ranks by completeness` | No credentials, 200; a complete candidate precedes a bare one; `total` is 2. |
| `candidates list shows staged and emitted candidates` | Both statuses present. |
| `candidates list filters by complete` | `filter[complete]=yes` returns only the complete one; `no` the other; `total` matches the filter. |
| `candidates list filters by an accepted domain` | A candidate whose `housing` code is only on one procedure (not accepted) is excluded by `filter[domain]=housing`; an accepted one is included. |
| `candidates list rejects an unknown domain code` | Negative: `filter[domain]=nope` is 422. |
| `candidates list rejects an unknown sort key and a bad limit` | Negative: `sort_by=secret` 422; `limit=101` rejected; `sort_order` without `sort_by` 422. |
| `candidates list searches titles in any locale` | `q=bescheid` matches a German title; case-insensitive; a literal `%` in `q` matches literally. |
| `candidates list pages deterministically` | Equal completeness and mentions, `limit=1`: each candidate once across pages. |
| `candidate card resolves the title for the requested locale` | `Accept-Language`/locale as the documents tests do: `en` title when present, else `de`. |
| `candidate description is the best mention excerpt` | Mentions `issued` (old), `form`, `required`: the `required` excerpt wins; cut at 300 characters; `description_source` is that procedure's title. |
| `candidate detail splits ingress and egress by edge direction` | Edge A requires B: A's ingress has B and no egress; B's egress has A. |
| `candidate detail merges duplicate edges per neighbour` | Two edges A-requires-B from two procedures: one neighbour; `is_optional` false if one edge is required. |
| `candidate detail hides a non-http portal url` | Negative: `portal_url="javascript:alert(1)"` is returned as `null`. |
| `candidate detail returns 404 for an unknown id` | Negative: random UUID 404; a non-UUID path 404/422 per the Litestar converter, asserted. |
| `candidate detail never exposes mention internals` | Negative: keys `extractor`, `extractor_version`, `artifact_id`, `catalogue_service_id` absent from the JSON. |
| `screenshot streams the newest image with immutable headers` | Two screenshots on two procedures; the newer bytes are returned; `Cache-Control` contains `immutable`; `ETag` is the sha256; content type as stored. |
| `screenshot answers 304 for a matching etag without reading the store` | `If-None-Match` equal: 304, the in-memory store records zero reads, the ledger is not charged. |
| `screenshot is 404 without an image` | Negative: candidate exists but has no screenshot: 404; unknown candidate: 404 with another message. |
| `screenshot is 503 over the read budget` | Negative: with the R2 read budget exhausted in the ledger, 503 and no bytes. |
| `screenshot is 503 when storage is not configured` | Negative: store unset gives the existing storage error, not a 500. |
| `detail screenshot field is a relative proxy path` | `screenshot.url` equals `/api/v1/candidates/{id}/screenshot`; null when none; no `X-Amz` or presigned query anywhere in the body. |
| `public routes have no auth guards` | Introspect the controller: `guards` empty (`candidates` controller), while the admin controllers keep theirs (pin both). |

Write and run these before implementing.

## Green

1. DTOs and `from_row`/builder functions (small, one per DTO).
2. `list_query.py` spec; filters and ordering using chapter 2's `completeness_subquery`, `completeness_order` and the existing `candidate_filter`/`candidate_sort` helpers where they apply (do not copy them).
3. Repository: page of candidate rows with completeness; the description pick; the edge neighbours query (both directions, merged); sources; newest screenshot artifact.
4. Service: assemble cards and detail; taxonomy names via `TaxonomyService`.
5. Controller (no `guards`), dependencies, router; register in `app/main.py`; error handlers and metered store.
6. Screenshot route with ETag/304 before any store access.

## Files

**Edit**

- new `apps/api/app/features/candidates/` (about six small modules) and `apps/api/app/schema/candidate/read.py`
- `apps/api/app/main.py` (register the router)
- `apps/api/app/features/discovery/repository/composite.py` only to expose methods chapter 2 already added
- `apps/api/tests/test_candidates_public_api.py` (new)
- `docs/operations/discovery-layer.md` route table is chapter 10's; do **not** edit here except the docs-sync test if it enumerates routes and fails

**Do not edit**

- Admin controllers, guards, models, migrations, `artifact_read.py` presign behaviour, the emit services
- The public documents feature

## Refactor gate

Audit the new controller (parameters per method, no inline queries), `service.py` (methods about 5 lines, one nesting level; use small DTO builders), the repository modules (about 100 lines each; split by aggregate: cards, neighbours, screenshot), the three-argument limit (use a query DTO beyond that), strict types (no `Any`), docstrings on public items. Check that nothing of the admin list code is duplicated (rule of three: admin list, public list, machine list); extract only what three callers share. Report the outcome.

## Verification

```bash
cd apps/api && pytest tests/test_candidates_public_api.py tests/test_candidate_completeness.py tests/test_documents_filter.py tests/test_discovery_artifacts_api.py tests/test_discovery_admin_list_query.py
cd ../.. && ./ci.sh
```

Also run `mypy app scripts` (inside `./ci.sh`) and `ruff format --check`. Record the response of one local `curl` to `/api/v1/candidates?limit=2` against the dev server in the PR description.

## Commits

`test(api): define the public candidate list and detail`, `feat(api): add the public candidate list and detail`, `test(api): define the candidate screenshot proxy`, `feat(api): serve candidate screenshots with immutable caching`.

## Out of scope

Presigned URLs, thumbnails, a curation or hide list, authentication, writing anything, search over mention text, the web client (chapters 5 to 7), the admin list (chapter 4).
