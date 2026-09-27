---
name: "Chapter 2 — Cast-vote service"
overview: "VoteService.cast upserts a user's vote on a pending suggestion, refusing self-votes and votes on non-pending suggestions; VoteService.remove deletes it."
todos:
  - id: repo
    content: "VoteRepository upsert, delete, get"
    status: pending
  - id: service
    content: "VoteService.cast and remove with the guard rules"
    status: pending
isProject: false
---

# Chapter 2 — Cast-vote service

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-cast-service` · **Status:** planned

**Depends on:** [1](01-vote-model-migration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Domain logic for casting and removing a vote, with the two rules that are not expressible as a database
constraint: no self-votes (D2), and only `pending` suggestions can be voted on.

## Design decisions

**Layering.** `VoteRepository` (`upsert(suggestion_id, user_id, value)` via `INSERT ... ON CONFLICT (...)
DO UPDATE SET value = excluded.value`, `delete`, `get`) → `VoteService` (rule checks, calls the repository,
calls `SuggestionService.get(id)` for status and submitter — a service-to-service read, never touching the
suggestion repository directly).

**Rule order**: unknown suggestion → `NotFoundError`; not `pending` → `SuggestionNotVotableError`; caller is
the submitter → `SelfVoteError`. Checked in that order so the most specific, cheapest check happens first.

**Idempotent same-value cast**: casting `+1` twice is a no-op (the upsert just rewrites the same value);
casting `-1` after `+1` flips it. Neither is an error — this is what "changing your mind" means (D1).

**`remove` is a no-op if there is no vote** (not an error), matching the object-store `delete` semantics
elsewhere in this program for consistency.

**No transition trigger here.** This chapter only writes the vote row; whether that changes the suggestion's
status is chapter 4/5's concern. Keeping vote-casting free of transition logic keeps this service small and
testable in isolation.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/voting/repository.py` | `VoteRepository` |
| `apps/api/app/features/voting/service.py` | `VoteService`, errors |
| `apps/api/app/features/voting/dependencies.py` | Providers |
| `apps/api/tests/test_vote_service.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `VoteService.cast · records an up-vote for a pending suggestion` | Row exists, value 1 |
| `VoteService.cast · changes an existing vote's value` | One row, new value |
| `VoteService.cast · casting the same value twice is a no-op` | Still one row, same value |
| `VoteService.cast · rejects voting on the caller's own suggestion` | `SelfVoteError` |
| `VoteService.cast · rejects voting on an approved suggestion` | `SuggestionNotVotableError` |
| `VoteService.cast · rejects voting on a rejected suggestion` | Same error |
| `VoteService.cast · rejects an unknown suggestion` | `NotFoundError` |
| `VoteService.remove · deletes an existing vote` | Row gone |
| `VoteService.remove · is a no-op when there is no vote` | No error |

## Green

1. Repository upsert/delete/get; happy-path cast; tests 1–3.
2. Self-vote and status guards; tests 4–7.
3. Remove; tests 8–9.

## Refactor gate

`cast` is three named guard calls plus the upsert, ≈5 LOC total. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_vote_service.py
cd ../.. && ./ci.sh
```

## Out of scope

HTTP (chapter 3), tallying (chapter 4), transitions (chapter 5).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-cast-service
```

```text
test(api): describe casting and removing votes, and the self-vote guard

feat(api): add VoteService
```
