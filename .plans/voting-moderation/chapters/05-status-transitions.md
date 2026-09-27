---
name: "Chapter 5 — Status transitions"
overview: "Casting a vote that crosses a threshold moves the suggestion to approved or rejected in the same request, through a single transition_to entry point that later chapters extend with promotion and logging."
todos:
  - id: transition
    content: "SuggestionService.transition_to(id, new_status, actor, reason=None)"
    status: pending
  - id: wire
    content: "VoteService calls transition_to after a successful cast"
    status: pending
isProject: false
---

# Chapter 5 — Status transitions

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-transitions` · **Status:** planned

**Depends on:** [4](04-tally-and-thresholds.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4, §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`SuggestionService.transition_to(id, new_status, actor)` is the one place that changes a suggestion's
status, called from the vote path when a threshold is crossed. This chapter wires the transition itself
(status column only); promotion (chapter 6–7) and event logging (chapter 8) extend the same method rather
than adding parallel status-changing code.

## Design decisions

**Single entry point (D5, D6).** `transition_to` lives on `SuggestionService` (suggestion-interface),
because status is that feature's own data; `VoteService.cast` calls it via
`suggestions_service.transition_to(...)` (service-to-service), never writing `suggestion.status` itself.
This is the same shape the override endpoint (chapter 9) will use later — one caller, one path, from day
one.

**Idempotent no-op on same status.** `transition_to(id, "pending")` when already `pending` does nothing
(guards against a threshold re-check after removing a vote from an already-pending suggestion). Transitioning
an already-`approved` or already-`rejected` suggestion again raises `AlreadyDecidedError` — status changes
exactly once (this is what makes promotion in chapter 6 safe to assume "runs exactly once").

**Wiring point in `VoteService.cast`**: after the upsert, recompute the tally (chapter 4) and call
`decide_status`; if the result differs from `pending`, call `transition_to`. This chapter's tests do not yet
assert promotion happens (chapters 6–7 add the created row); they assert the **status column** changes.

**`remove` (unvote) never triggers a transition.** Only casting can push a suggestion over a threshold;
removing a vote pulls the score back but a suggestion that is already `approved`/`rejected` does not revert
(D-open-seam: no "reopening").

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/service.py` | `transition_to`, `AlreadyDecidedError` |
| `apps/api/app/features/voting/service.py` | Call `transition_to` after a threshold-crossing cast |
| `apps/api/tests/test_suggestion_transitions.py`, updates to `test_vote_service.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `transition_to · pending to approved changes the status column` | Direct call |
| `transition_to · pending to pending is a no-op` | No error, unchanged |
| `transition_to · approved to anything raises AlreadyDecidedError` | Guard |
| `transition_to · rejected to anything raises AlreadyDecidedError` | Guard |
| `VoteService.cast · a vote that reaches the approve threshold moves the suggestion to approved` | End-to-end through voting |
| `VoteService.cast · a vote that reaches the reject threshold moves the suggestion to rejected` | Symmetric |
| `VoteService.cast · a vote that does not cross a threshold leaves the suggestion pending` | Negative |
| `VoteService.cast · once approved, a later vote from a different user is rejected as not votable` | Regression from chapter 2's guard, now reachable through a real transition |
| `VoteService.remove · never triggers a transition` | Score drops, status unchanged |

## Green

1. `transition_to` and its guard; tests 1–4.
2. Wire into `cast`; tests 5–7.
3. Regression and remove behaviour; tests 8–9.

## Refactor gate

`transition_to` stays ≈5 LOC at this chapter (status write plus the no-op/guard checks); chapters 6–8 extend
it and must re-justify its size against the ~5 LOC target or extract a `SuggestionTransition` handler
object. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_transitions.py tests/test_vote_service.py
cd ../.. && ./ci.sh
```

## Out of scope

Promotion (chapters 6–7), event logging (chapter 8), moderator override (chapter 9).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-transitions
```

```text
test(api): describe status transitions and threshold-triggered voting

feat(api): add transition_to and wire threshold-crossing votes
```
