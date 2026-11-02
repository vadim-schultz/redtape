---
name: "Chapter B2 — Suggestion core"
overview: "Polymorphic submitters replace the repeated user/crawler switch, SuggestionFilters flows through the repository as one value, KindHandler becomes generic over its payload, and dead parameters and pointless delegations go."
todos:
  - id: characterize
    content: "Pin create/replay/event/row behaviour per submitter kind and the list filters"
    status: pending
  - id: submitter
    content: "Replace SubmitterRef(kind, id) with HumanSubmitter and CrawlerSubmitter that own their rules"
    status: pending
  - id: filters
    content: "Move SuggestionFilters below the service; repository takes it directly; delete _FilterKwargs"
    status: pending
  - id: typed-handlers
    content: "KindHandler[PayloadT] plus one narrowing adapter; no Any"
    status: pending
  - id: hygiene
    content: "Remove dead parameters; decide each one-line delegation by the boundary test"
    status: pending
isProject: false
---

# Chapter B2 — Suggestion core

**Repo:** `redtape` · **Branch:** `refactor/suggestion-core` · **Status:** planned

**Depends on:** A1 (vote and promotion errors) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L1, L2, L14, section 5 row `handlers.py`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/features/suggestions/{service,repository,handlers}` (plus the additions listed under Parallel notes)

**Findings:** L1, L2, L14 (suggestions part), T5 (`KindHandler`), dead parameters, API one-line delegations

## Goal

`SuggestionService` contains no `if submitter.kind == ...` branch. The suggestion filters travel as one `SuggestionFilters` value from query parameters to SQL. `KindHandler` is typed per payload without `Any`. Unused parameters are gone. Behaviour, status codes and JSON are unchanged.

## Verified switch sites (L1)

All in `apps/api/app/features/suggestions/service.py` unless noted. `SubmitterRef.kind` is `Literal["user", "crawler"]` (line 65).

| Line | Decision made on `submitter.kind` | Becomes |
| --- | --- | --- |
| 49 | `_SUBMITTER_COLUMN` maps kind to `submitted_by_user_id` / `submitted_by_api_key_id` | `submitter.row_fields()` |
| 50, 227 | `_SUBMITTER_SOURCE` maps kind to `SuggestionSource.HUMAN` / `CRAWLER` | `submitter.source_type` |
| 174, 176 | `_replay`: only crawlers honour an idempotency key; looks up by `api_key_id=submitter.id` | `submitter.find_replay(repo, key)` (human returns `None`) |
| 179 | `_validate_source_url`: only crawlers must send `source_url` | `submitter.check_source_url(request.source_url)` (raises `MissingSourceUrlError`) |
| 195, 196 | `_log_submitted`: which of `actor_user_id` / `actor_api_key_id` is set | `submitter.event_actor()` |
| 232 | `idempotency_key if submitter.kind == "crawler" else None` | `submitter.stored_idempotency_key(key)` |
| 233 | `**{_SUBMITTER_COLUMN[...]: submitter.id}` | `**submitter.row_fields()` |

Outside the service, the same distinction exists in: `suggestions/submitter.py:10-12` (`isinstance(principal, UserPrincipal)` mapping, two arms, the only boundary mapping that stays), `schema/suggestion/read.py:13-15` (`_SUBMITTER_KIND`, persisted `source_type` to wire `kind`; stays, it is the response contract), `auth/principal.py:15,28` (`kind` strings; owned by B3), and the constructors `SubmitterRef("crawler", api_key.id)` at `features/discovery/candidate_emit.py:86` and `features/discovery/emit.py:78` (type at `emit.py:11,42,96`).

## Design

Two frozen dataclasses in a new `apps/api/app/features/suggestions/submitters.py`, implementing one `Submitter` protocol:

| Member | `HumanSubmitter(user_id)` | `CrawlerSubmitter(api_key_id)` |
| --- | --- | --- |
| `source_type` | `SuggestionSource.HUMAN` | `SuggestionSource.CRAWLER` |
| `row_fields()` | `{"submitted_by_user_id": user_id}` | `{"submitted_by_api_key_id": api_key_id}` |
| `find_replay(repo, key)` | `None` (D8: a human's header is ignored) | `repo.get_by_idempotency_key(api_key_id=..., idempotency_key=key)` when `key` is set |
| `check_source_url(url)` | no-op | raises `MissingSourceUrlError` when `url is None` (D9) |
| `stored_idempotency_key(key)` | `None` | `key` |
| `event_actor()` | `(user_id, None)` | `(None, api_key_id)` as a small `NamedTuple` |

`MissingSourceUrlError` moves to `submitters.py` and is re-exported by `service.py` (controller imports it from the service today). The `submitter_ref` mapper in `submitter.py` becomes `submitter_for(principal)` (rename is optional; keep `submitter_display_name`). `Submission.submitter` is typed `Submitter`.

Why classes and not a dict per kind: this is the textbook replace-conditional-with-polymorphism case, there are already seven arms, and a third principal kind would otherwise touch all of them.

`SuggestionFilters` (L2) moves out of `service.py` into `apps/api/app/features/suggestions/filters.py` (frozen dataclass, same four fields, same defaults). `service.py` keeps re-exporting it (it is in `__all__` and `query.py:10` imports it from there). Repository signatures become `count(filters)`, `list_page(filters, *, offset, limit)` and `_apply(stmt, filters)`. Delete `_FilterKwargs` and `_filter_kwargs` (`service.py`, between `SuggestionFilters` and `class SuggestionService`). The only callers of `repo.count` / `repo.list_page` are `service.py:154-155`; no test calls them directly.

Typed handlers (T5). The service correlates `request.kind` with `request.payload` (a union, `schema/suggestion/create.py`), which no type checker can express through a dict. So:

1. `class KindHandler(Protocol[PayloadT])` in `handlers.py` with `payload_type: ClassVar[type[PayloadT]]`, `validate(payload: PayloadT, *, jurisdiction_id)`, `normalized_url(payload: PayloadT)`, `conflicts(payload: PayloadT, *, jurisdiction_id)`. `PayloadT` is bound to `NewDocumentPayload | NewRequirementPayload` and contravariant.
2. A `Promoter` protocol with only `promote(suggestion) -> UUID`. `SuggestionTransitions` takes `dict[SuggestionKind, Promoter]` (it only calls `promote`, `transitions.py:62`).
3. One generic adapter `KindDispatch(Generic[PayloadT])` that holds a `KindHandler[PayloadT]`, narrows the union once with `isinstance(payload, handler.payload_type)` (raising a precise `PayloadKindMismatchError` otherwise) and forwards. `SuggestionService._handlers` becomes `dict[SuggestionKind, KindDispatch[...]]`-like through a non-generic `Dispatch` protocol over the union.

Constraint: it must pass `uv run mypy app scripts` with no `Any`, no `cast`, no `type: ignore`. If the adapter does not type-check, fall back to narrowing with `match request.payload:` in exactly one private method and record the reason in the PR.

Handler construction. `NewRequirementHandler.__init__` takes `taxonomy` and never uses it (`handlers.py` lines 121-125); the uniform constructor in the `KindHandler` protocol (lines 45-47) forces it. Replace the three positional parameters by one frozen `HandlerDeps(documents, taxonomy, suggestions)`; each handler reads what it needs. `KIND_HANDLERS` (lines 191-194, pinned by `tests/test_suggestion_requirement_kind.py:291`) stays a class registry.

## Dead parameters and one-line delegations (verified)

| Item | Finding | Decision |
| --- | --- | --- |
| `SuggestionService.transition_to(.., reason)` (`service.py:167,170`) and `SuggestionTransitions.transition_to(.., reason)` (`transitions.py:40`) | `reason` is never read in either. No caller passes it (tests and `voting/service.py:82` use `actor=None`). | Remove from both. |
| `NewRequirementHandler.__init__(.., taxonomy, ..)` | Unused. | Gone with `HandlerDeps`. |
| `NewDocumentHandler.validate(.., jurisdiction_id)` (`handlers.py:80`) | Unused in the body, **but the protocol requires it** because `NewRequirementHandler.validate` uses it (`:127-131`). | **Not dead.** The audit is wrong here; leave it and say so in the PR. |
| `NewRequirementHandler.normalized_url(payload)` (`:140`) | Same: protocol-mandated. | Leave. |
| `SuggestionService.get` (`service.py:149`) | One caller, `voting/service.py:64`, across a feature boundary. | Keep (inlining would make `VoteService` depend on `SuggestionRepository`). Add a docstring. |
| `SuggestionService.transition_to` itself | Facade over `SuggestionTransitions`, called by `VoteService` and ~30 tests. | Keep. |
| `VoteService.tally_for` / `tally_for_many` (`voting/service.py:53-57`) | Callers are `suggestions/controller.py:64,107`; inlining makes a controller call a repository. | Keep; a layer boundary is not a one-line wrapper smell. |
| `DocumentService.get_document_jurisdiction`, `requirement_exists`, `requires_directly` (`documents/service.py:168-186`) | Real one-line delegations, but the file belongs to B3 and the handlers depend on `DocumentService` by design. | Out of scope here; B3's narrow port decides them. |

Test with every delegation: does it cross a layer or feature boundary the caller must not skip? If yes keep and document; if no, inline.

## Files

- `apps/api/app/features/suggestions/service.py`: remove `_SUBMITTER_*`, `SubmitterRef`, `_FilterKwargs`, `_filter_kwargs`; use the polymorphic submitter; drop `reason`.
- New `apps/api/app/features/suggestions/submitters.py` and `filters.py`.
- `apps/api/app/features/suggestions/repository.py`: `_apply`, `count`, `list_page` take `SuggestionFilters`.
- `apps/api/app/features/suggestions/handlers.py`: generics, `HandlerDeps`, `Promoter`, `KindDispatch`.
- `apps/api/app/features/suggestions/transitions.py`: `Promoter`, no `reason` (A1 already edited this file; build on its result).
- `apps/api/app/features/suggestions/submitter.py`, `submission.py`: new submitter type.
- `apps/api/app/features/discovery/candidate_emit.py:16,86` and `emit.py:11,42,78,96`: construct `CrawlerSubmitter(api_key.id)`. A2 restructures these files; edit whatever A2 left, nothing more.
- Tests to update mechanically: `tests/test_suggestion_duplicates.py` (about a dozen `SubmitterRef("user", user.id)` calls), `tests/test_suggestion_service.py`, `tests/test_discovery_candidate_emit.py`, `tests/test_suggestion_requirement_kind.py`.

## TDD loop

### Red

Characterise on the unchanged code first (all green):

1. Per submitter kind, through `SuggestionService.create`: `test_human_row_has_user_column_source_human_and_no_idempotency_key` (also with a key supplied: stored as `None`), `test_crawler_row_has_api_key_column_source_crawler_and_stored_key`, `test_crawler_replay_returns_existing_row_with_replayed_true`, `test_human_idempotency_header_is_ignored`, `test_crawler_without_source_url_raises_missing_source_url`, `test_human_without_source_url_is_accepted`, `test_submitted_event_actor_matches_kind` (extends `test_suggestion_service.py:142,156`).
2. Filters: `test_list_filters_by_status_kind_source_type_and_jurisdiction` (each alone, then combined) and `test_empty_filters_return_everything_newest_first`, `test_count_matches_list_total_under_filters`, plus a negative `test_filter_with_no_match_returns_empty_page_and_zero_total`.
3. Handlers: `test_new_requirement_handler_rejects_cycle`, `test_promote_new_document_raises_promotion_conflict_when_slug_taken` already exist (`test_promote_*`); confirm they run.

Then the new red tests:

4. `tests/test_suggestion_submitters.py`: unit tests of `HumanSubmitter` and `CrawlerSubmitter` (each member in the design table; negative: `CrawlerSubmitter.check_source_url(None)` raises). Fail: module missing.
5. `test_service_has_no_submitter_kind_switch`: a source scan asserting `'.kind ==' not in` `service.py` text and `SubmitterRef` absent (cheap structural guard; delete it if G2 adds a general one).
6. `test_kind_dispatch_rejects_payload_of_the_wrong_kind`: a `new_requirement` payload given to the document handler raises `PayloadKindMismatchError`.
7. `test_transition_to_has_no_reason_parameter` via `inspect.signature`.

### Green

1. Add `submitters.py`; switch `submitter.py`, `submission.py`, `service.py`, discovery emit call sites, tests.
2. Add `filters.py`; change repository and service; delete the TypedDict.
3. Make `handlers.py` generic; add `Promoter`, `HandlerDeps`, `KindDispatch`; run mypy until clean without escapes.
4. Remove `reason` and the unused constructor parameter.

### Refactor

Gate: judge by responsibility, not line count. `SuggestionService` should read as "orchestrate create/read/transition" with no submitter or filter bookkeeping; if `create` still needs a comment to explain its steps, check the order of validate, source-url, duplicates, build, insert (it must not change). Apply the rule of three to the submitter members (do not add a member for a single use), keep one nesting level, no one-line wrappers beyond the boundary cases decided above, no new `Any`, a docstring on every new public symbol (imperative mood, intent not signature). Remove the `D` and `ANN401` baseline entries of every file this chapter rewrites (`service.py`, `handlers.py`, `repository.py`, `submitter.py`, `submission.py`, `query.py`, `dependencies.py` and the two new files). Record `Refactor gate: smells found -> ..., refactorings applied -> ...` with before and after `measure_code_rules.py` numbers (`SuggestionService` is 124 lines today; the target is by responsibility, not size).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_suggestion_submitters.py tests/test_suggestion_service.py tests/test_suggestion_duplicates.py \
  tests/test_suggestion_transitions.py tests/test_suggestion_requirement_kind.py tests/test_suggestions_submit.py \
  tests/test_suggestions_machine_submit.py tests/test_suggestions_read.py tests/test_promote_new_document.py \
  tests/test_promote_requirement_edge.py tests/test_vote_service.py tests/test_discovery_candidate_emit.py
cd ../..
./ci.sh
```

## Parallel notes

Runs in batch 2 alongside T1 step 2, B3, B4, I1, I2, W3, W4. Do not touch `features/documents/*` and `features/auth/*` (B3: it owns the `DocumentService` delegations and `auth/principal.py`), `features/discovery/{stage_sync,pipeline_rows,task_enqueue}.py` (B4), or `schema/discovery/*` (B3). The `discovery/{emit,candidate_emit}` edits are limited to the submitter constructor and import; A2 has merged by then. L11 in the finding map is assigned to B3 whose touches exclude `suggestions/`; B2 does not move handler construction out of `SuggestionService.__init__` (it keeps the constructor signature that seven test modules use) and records that as a deferred half of L11. A docstring-only pass over the same directory (T1 step 2, slice `features/suggestions`) must land before or after this chapter, never concurrently: schedule it after.
