---
name: "Chapter 4 — Tally and thresholds"
overview: "SuggestionRead gains tally {up, down, score} and, when authenticated, my_vote; Settings gains the approve and reject thresholds; a pure function decides the resulting status for a score."
todos:
  - id: settings
    content: "vote_approve_threshold, vote_reject_threshold"
    status: done
  - id: tally
    content: "VoteRepository.tally_for, service composition into SuggestionRead"
    status: done
  - id: decide
    content: "decide_status(score, thresholds) pure function"
    status: done
isProject: false
---

# Chapter 4 — Tally and thresholds

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-tally` · **Status:** implemented, PR open

**Depends on:** [3](03-vote-endpoints.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Every suggestion read shows its vote count (D3: computed, never cached), and the pure rule that turns a
score into a status exists and is tested before chapter 5 wires it into an actual transition.

## Design decisions

**`VoteRepository.tally_for(suggestion_id) -> Tally`**: one `GROUP BY value` aggregate query, no N+1 for
list pages (`tally_for_many(ids) -> dict[UUID, Tally]`, one query for the whole page, same shape as the
matrix endpoint's aggregate-not-loop lesson).

**Settings**: `vote_approve_threshold: int = 3`, `vote_reject_threshold: int = -3`; a validator rejects
`vote_reject_threshold >= vote_approve_threshold` at startup (a misconfiguration that would make every
vote instantly resolve).

**`decide_status(score: int, approve: int, reject: int) -> SuggestionStatus`** is a free function in
`features/voting/thresholds.py`: `score >= approve` → `approved`; `score <= reject` → `rejected`; else
`pending`. It takes no session and no request — this is what chapter 5 calls, and what this chapter's tests
exhaustively cover so chapter 5 only needs to test the wiring.

**Composition point**: `SuggestionService.get_suggestion`/`list_suggestions` (suggestion-interface chapter
7) is extended with an optional `voting_service` collaborator behind a small
`with_tally(suggestions_service, voting_service)` composition in the controller — the same "composition in
the controller" pattern the matrix endpoint set (documents × taxonomy), not a new cross-service dependency
baked into `SuggestionService` itself. `my_vote` is included only when a `current_user` (optional) is
present.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/config.py` | Two settings, validator |
| `apps/api/app/features/voting/repository.py` | `tally_for`, `tally_for_many` |
| `apps/api/app/features/voting/thresholds.py` | `decide_status` |
| `apps/api/app/schema/suggestion/read.py` | `Tally`, `SuggestionRead.tally`, `.my_vote` |
| `apps/api/app/features/suggestions/controller.py` | Compose tally into responses |
| `apps/api/tests/test_vote_tally.py`, `test_thresholds.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `tally_for · counts up and down votes and computes score` | Known fixture |
| `tally_for · a suggestion with no votes has zeros` | Boundary |
| `tally_for_many · returns one query's worth of tallies for a page of ids` | Query-count guard |
| `decide_status · below both thresholds stays pending` | Table |
| `decide_status · at or above the approve threshold is approved` | Boundary |
| `decide_status · at or below the reject threshold is rejected` | Boundary |
| `Settings · rejects reject_threshold >= approve_threshold` | Validation error at construction |
| `GET /suggestions/{id} · includes the tally` | Shape |
| `GET /suggestions/{id} · includes my_vote when authenticated` | Value matches the caller's vote |
| `GET /suggestions/{id} · omits my_vote when anonymous` | `null`, not an error |
| `GET /suggestions · list responses include a tally per item without N+1` | Query-count guard |

## Green

1. Settings and validator; test 7.
2. `tally_for`/`tally_for_many`; tests 1–3, 11.
3. `decide_status`; tests 4–6.
4. Response composition; tests 8–10.

## Refactor gate

`decide_status` is a two-branch function, no nesting. Composition helper stays ≤ ~10 LOC. Report the
outcome.

**Outcome:** `decide_status` is two `if`s and a fallthrough return, no nesting, exactly as scoped.
`with_tally` (in `suggestions/controller.py`) is a 2-line body doing one `model_copy(update=...)`, well
under the ≤10 LOC budget; both `get_suggestion` and `list_suggestions` call it, `list_suggestions` first
batching through `tally_for_many` so the composition itself stays free of query concerns. `tally_for`/
`tally_for_many` share a `_tally(up, down) -> Tally` helper rather than duplicating the score computation.
No new cross-service dependency was added to `SuggestionService` — `suggestions_router` now takes its
dependency dict from `voting.dependencies` (which already merges the suggestion deps and adds
`vote_service`) the same way `taxonomy_router` takes its dict from `documents.dependencies`, avoiding a
circular import between the two features' dependency modules.

## Verification

```bash
cd apps/api
python -m pytest tests/test_vote_tally.py tests/test_thresholds.py tests/test_suggestions_read.py
cd ../.. && ./ci.sh
```

## Out of scope

Actually transitioning status (chapter 5), promotion (chapters 6–7).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-tally
```

```text
test(api): describe vote tallies, thresholds and the status decision rule

feat(api): add tally, my_vote and the decide_status rule
```
