---
name: "A1 — Vote and promotion errors"
overview: "A promotion conflict while voting returns 409 and keeps the vote instead of a 500 that rolls it back; removing a vote after a decision is rejected; a missing suggestion in a transition is a typed 404; the pending row is read with SELECT ... FOR UPDATE."
todos:
  - id: pin
    content: "Characterise today: vote happy paths, threshold transitions, promotion conflicts at service level"
    status: pending
  - id: red
    content: "Red tests: promotion conflict during vote, remove after decision, typed not-found, FOR UPDATE, stale identity map"
    status: pending
  - id: green
    content: "CastResult, typed errors, status mapping, locked pending read, remove guard"
    status: pending
isProject: false
---

# A1 — Vote and promotion errors

**Repo:** `redtape` · **Branch:** `fix/vote-promotion-errors` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (C1, C7) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/features/voting`, `api/features/suggestions/{controller,handlers,transitions}`. **After:** none.

**Findings:** C1, C7.

## Goal

Every failure of the vote paths maps to a deliberate status code, and a final decision is never changed afterwards:

- A vote that crosses the approve threshold but whose promotion conflicts (the slug, URL or requirement edge was taken in the meantime) answers **409** with the vote kept and the suggestion still `pending`. Today it is a 500 and `provide_session` rolls the vote back.
- `VoteService.remove` rejects a suggestion that is no longer pending (409) or does not exist (404).
- `transitions.py` raises a typed `SuggestionNotFoundError` instead of a bare `ValueError`.
- `SuggestionTransitions._get_pending` reads the row with `SELECT ... FOR UPDATE`, so two concurrent casts cannot both decide.

## Intentional status-code changes (the only behavioural changes)

| Request | Today | After |
| --- | --- | --- |
| `PUT /suggestions/{id}/vote`, vote reaches a threshold, promotion conflicts | 500; the whole session is rolled back, the vote is lost | **409**, body `{"status_code": 409, "detail": ..., "extra": {...}}`, vote kept, suggestion stays `pending` |
| `PUT .../vote`, suggestion was decided by a concurrent request after our read | 500 (`AlreadyDecidedError` is a `ValueError` nobody catches) | **409**, vote not kept (it would change a final tally) |
| `DELETE .../vote`, suggestion approved or rejected | 204, and the tally of a final decision changes | **409**, nothing changes |
| `DELETE .../vote`, unknown suggestion | 204 (deleting zero rows) | **404** |

Unchanged: cast on a non-pending suggestion 409, own suggestion 403, unknown suggestion 404, delete on a pending suggestion 204 (with or without a vote), response body of a successful `PUT` `{"ok": true, "value": n}`. The PR text lists the four changes; `docs/operations/suggestion-api.md` (mentions the vote routes at lines 9-10) gets one sentence with the new codes.

## Files (verified)

| File | Lines | Change |
| --- | --- | --- |
| `apps/api/app/features/voting/service.py` | `cast` 41-48, `remove` 50-51, `_get_suggestion` 63-67, `_maybe_transition` 77-82 | `cast` returns `CastResult`; `_maybe_transition` catches `PromotionConflictError`; `remove` loads the suggestion and applies `_check_pending` |
| `apps/api/app/features/voting/controller.py` | `VOTE_ERROR_STATUS` 15-19, `_to_http` 22-23, `cast` 31-37, `remove` 39-41 | map `AlreadyDecidedError` and `SuggestionNotFoundError`; catch `tuple(VOTE_ERROR_STATUS)` in `cast` and `remove`; return the 409 `Response` when the promotion was blocked |
| `apps/api/app/features/suggestions/transitions.py` | `AlreadyDecidedError` 17, `_get_pending` 53-59 (bare `ValueError` at 56) | add `SuggestionNotFoundError(ValueError)`; `_get_pending` uses the locked read |
| `apps/api/app/features/suggestions/repository.py` | `get` 47-48 | add `get_for_update` (`select(...).with_for_update().execution_options(populate_existing=True)`) |
| `apps/api/app/features/suggestions/service.py` | `__all__` 33-47 | export `SuggestionNotFoundError` beside `AlreadyDecidedError` |
| `apps/api/app/features/suggestions/handlers.py` | `PromotionConflictError` 30 | no change; named here because voting imports it through `suggestions.service` (re-exported, `service.py:19,39`) |

Facts that correct the audit: `_STATUS_BY_ERROR` in `suggestions/controller.py:29-36` is not the fix site. Only the voting path reaches `transition_to` (`voting/service.py:82` is its sole production caller; every other caller is a test), and the suggestions controller's `create` never promotes. `main.py:42` installing only object-store handlers is true but irrelevant to the fix because the mapping stays in the controller, as for every other feature. Two edits fall outside the table's Touches: `suggestions/repository.py` and `suggestions/service.py` (one method, one `__all__` entry). B2 (`After: A1`) owns both files next, so there is no parallel conflict; the PR notes it.

Why `CastResult` and not an exception: Litestar throws any handler exception into the `provide_session` generator (`litestar/_kwargs/cleanup.py`, `DependencyCleanupGroup.close(exc)` -> `_throw`), and `provide_session` (`app/db.py`) rolls back on exception. A 409 raised as `HTTPException` would therefore also discard the vote. A kept vote needs a normal return, so the service reports the blocked promotion as data and the controller turns it into a `Response` with status 409.

```python
@dataclass(frozen=True, slots=True)
class CastResult:
    """Outcome of casting a vote: the stored vote, and why the suggestion was not decided if a threshold was crossed."""
    vote: SuggestionVote
    promotion_blocked: str | None = None   # PromotionConflictError message; None when nothing blocked
```

No savepoint is needed: every `promote` implementation checks its preconditions (`_check_still_free`, `_check_still_valid`) before it writes (`handlers.py` `NewDocumentHandler.promote` and `NewRequirementHandler.promote`), so a `PromotionConflictError` leaves the session untouched. A conflict that only the database detects (unique-constraint `IntegrityError` after both checks passed) is out of scope; see Open seam.

## TDD loop

Tests go into the existing files so fixtures (`jurisdiction`, `submitter`, `voter`, `_suggestion`, `service`) are reused: `tests/test_vote_service.py`, `tests/test_vote_endpoints.py`, `tests/test_suggestion_transitions.py`. Run with Postgres (`REQUIRE_DB=1`); the API suite skips otherwise.

### Characterise first (green before any change)

- `test_cast_a_vote_that_reaches_the_approve_threshold_moves_the_suggestion_to_approved`, `..._reject_threshold_...`, `..._does_not_cross_a_threshold_leaves_the_suggestion_pending`, `test_cast_once_approved_a_later_vote_..._not_votable` (all exist, `test_vote_service.py:193-230`).
- `test_put_vote_returns_409_for_a_non_pending_suggestion`, `..._404_for_an_unknown_suggestion`, `..._403_for_the_suggestions_own_submitter` (exist, `test_vote_endpoints.py:183-212`).
- `test_a_url_less_suggestion_racing_for_a_taken_slug_fails_on_the_slug_alone` (`test_promote_new_document.py:129`) and the three `pytest.raises(PromotionConflictError)` cases in `test_promote_requirement_edge.py` (lines 175, 193, 212) prove the handlers' conflict behaviour; this chapter does not change them.

### Red (new tests, written first, must fail for the stated reason)

**Service (`test_vote_service.py`)**

1. `test_cast_that_hits_a_promotion_conflict_keeps_the_vote_and_leaves_the_suggestion_pending` — arrange a competing document with the same slug (recipe: `test_promote_new_document.py:129-136`, approve a first suggestion of the same title through `SuggestionService.transition_to`), two voters cast +1 on the second suggestion, a third casts +1. Assert: no exception; `result.promotion_blocked` mentions the slug; the third voter's `SuggestionVote` row exists; `suggestion.status == PENDING`; events contain `VOTED` x3 and no `PROMOTED` or `STATUS_CHANGED` for it. Fails today with `PromotionConflictError`.
2. `test_cast_without_a_conflict_reports_nothing_blocked` — happy path: `result.promotion_blocked is None` for the threshold-crossing vote that promotes, and for a sub-threshold vote.
3. `test_a_blocked_promotion_is_retried_by_the_next_vote` — after test 1's state, delete the competing document, cast a fourth +1: the suggestion becomes `APPROVED`, document exists. (Negative-to-positive: shows the vote kept is not a dead end.)
4. `test_cast_propagates_already_decided_when_the_suggestion_was_decided_behind_its_back` — monkeypatch `SuggestionService.transition_to` to raise `AlreadyDecidedError`; `service.cast` re-raises it (the controller maps it).
5. `test_remove_on_an_approved_suggestion_is_rejected_and_keeps_the_vote` and `..._on_a_rejected_suggestion_...` — expects `SuggestionNotVotableError`; vote row still present; status unchanged. Fails today (returns `None`, deletes the vote).
6. `test_remove_on_an_unknown_suggestion_raises_not_found` — expects `NotFoundError`.
7. Replace `test_remove_never_triggers_a_transition` (`test_vote_service.py:244`): it asserts that removing a vote after approval silently succeeds, which is exactly the defect. New body: after approval, `remove` raises `SuggestionNotVotableError`, status stays `APPROVED`, the voter's row is still there. Rename to `test_remove_after_a_decision_is_rejected_and_changes_nothing`.
8. Keep `test_remove_deletes_an_existing_vote` and `test_remove_is_a_no_op_when_there_is_no_vote` unchanged (pending suggestion, happy and idempotent paths).

**Transitions (`test_suggestion_transitions.py`)**

9. `test_transition_to_an_unknown_suggestion_raises_suggestion_not_found` — `SuggestionNotFoundError`, and `issubclass(SuggestionNotFoundError, ValueError)` stays true (callers that caught `ValueError` keep working).
10. `test_transition_reads_the_pending_row_with_for_update` — attach `event.listen(db_session.get_bind(), "before_cursor_execute", ...)`, call `transition_to`, assert one captured statement matches `SELECT ... FROM suggestion ... FOR UPDATE`.
11. `test_transition_sees_a_status_changed_behind_the_identity_map` — load the suggestion (so the ORM holds `PENDING`), flip the column with a Core `update(Suggestion).values(status=APPROVED)`, then `transition_to` must raise `AlreadyDecidedError`. Fails without `populate_existing=True`, because `with_for_update` alone does not refresh an already-loaded instance. This is the test that makes the lock meaningful.

**HTTP (`test_vote_endpoints.py`)** — add a fixture `rollback_spy` that replaces `app.main.provide_session` (the existing `client` fixture patches it with `lambda: db_session`, which never rolls back) with a generator that yields `db_session` and appends to a list in `except`; the production `provide_session` in `app/db.py` has exactly this shape.

12. `test_put_vote_returns_409_and_keeps_the_vote_when_the_promotion_is_blocked` — two votes in the database, third via HTTP: status 409, `body["extra"]` carries the vote value, `rollback_spy` list is empty, `_vote_row(...)` is not `None`, suggestion `PENDING`.
13. `test_put_vote_returns_409_when_the_suggestion_was_decided_concurrently` — patch `SuggestionTransitions.transition_to` to raise `AlreadyDecidedError`: status 409 (not 500); `rollback_spy` records one rollback (the vote is discarded).
14. `test_delete_vote_returns_409_for_a_decided_suggestion_and_keeps_the_vote`, `test_delete_vote_returns_404_for_an_unknown_suggestion`.
15. Unchanged and still green: `test_delete_vote_removes_an_existing_vote`, `test_delete_vote_is_a_no_op_when_there_is_no_vote` (pending suggestion), `test_delete_vote_returns_401_without_a_token`.

Run the narrow suite and confirm tests 1, 5, 6, 7, 9, 10, 11, 12, 13, 14 fail for the stated reasons and 2, 3, 4, 8, 15 and the characterisation set pass or are skipped as noted. Record before/after counts.

### Green

1. `transitions.py`: add `SuggestionNotFoundError`; `_get_pending` calls `self._repo.get_for_update(suggestion_id)`.
2. `repository.py`: `get_for_update` as above; docstring states that the caller must be in a transaction and that it refreshes a loaded instance.
3. `voting/service.py`: `CastResult`; `cast` returns it; `_maybe_transition` returns `str | None` (the conflict message) after `except PromotionConflictError as exc: return str(exc)`; do not catch `AlreadyDecidedError`. `remove` becomes: `suggestion = self._get_suggestion(suggestion_id); self._check_pending(suggestion); self._repo.delete(...)`. Update `__all__` and the module docstring.
4. `voting/controller.py`: add `AlreadyDecidedError: HTTP_409_CONFLICT` and `SuggestionNotFoundError: HTTP_404_NOT_FOUND` to `VOTE_ERROR_STATUS`; both handlers `except tuple(VOTE_ERROR_STATUS)`; `cast` returns `Response` with status 409 and an `HTTPException`-shaped body when `result.promotion_blocked` is set (so clients parse it like every other 409), else `VoteRead(value=...)`.
5. Re-run the narrow suite until green.

### Refactor

**Refactor gate.** Smells to check: the three `ValueError` subclasses in `voting/service.py` plus `AlreadyDecidedError`/`SuggestionNotFoundError`/`PromotionConflictError` now feed one status table (`VOTE_ERROR_STATUS`), which is the right owner; do not invent a shared base class for them (two arms of a dict, not a hierarchy). `_to_http` stays one expression. `cast` and `remove` both start with `_get_suggestion` + `_check_pending`; with two uses that is below the rule of three (total arms for one decision, pre-existing included: `cast` also adds `_check_not_self`), so do not extract a combined helper. Judge by responsibility: `VoteService` owns "may this vote happen", `SuggestionTransitions` owns "status changes"; the lock lives with the latter, the guard with the former, and neither does the other's job. One nesting level, at most three parameters. New public symbols (`CastResult`, `SuggestionNotFoundError`, `SuggestionRepository.get_for_update`) get docstrings in imperative mood stating intent (not the signature); the files this chapter rewrites (`voting/service.py`, `voting/controller.py`) get their missing docstrings too (T1 baseline for `features/voting` is directory-wide, so the line is removed by the T1 slice that finishes the directory, not here). No new `Any`, no `cast`, no `# type: ignore`.

## Not in scope (open seam)

- A promotion conflict that only the database detects (two promotions pass `_check_still_free`, one fails on the unique slug constraint with `IntegrityError`) still surfaces as a 500. Fixing it needs a savepoint around `promote` and an `IntegrityError` -> `PromotionConflictError` translation in the handlers; take it when a real race is observed.
- `VoteService.remove` checks pending with a plain read, so a `remove` racing a concurrent decision can still slip through. Locking it needs a locked read exposed through `SuggestionService`, which B2 is about to trim; revisit there.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_vote_service.py tests/test_vote_endpoints.py tests/test_suggestion_transitions.py tests/test_promote_new_document.py tests/test_promote_requirement_edge.py tests/test_vote_tally.py
cd ../..
./ci.sh
```

Run the narrow suite first, then `uv run pytest` in the background. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` and the before/after pass counts in the PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b fix/vote-promotion-errors
```

```text
test(api): pin vote errors, red for promotion conflict, remove after decision and locked read
fix(api): keep the vote and answer 409 when a promotion is blocked, guard remove, lock the pending row
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T2, T3, A2, A3, A4, B1, B6, W1, W2. Files this chapter must not touch: `features/discovery/*` (A2), `features/documents/*` and `features/auth/*` (B3), `lifespan.py` (A4), `routes.py`, `shared/locale.py` and `suggestions/slugs.py` (B1), `services/openplz_client.py` and `scripts/` (B6), ruff and mypy config (T1, T2), and `tests/test_architecture.py` (T3; the new guard scans `voting/` and `suggestions/` and must stay green, which it does because this chapter adds no `litestar` import to a service). B2 (`After: A1`) later reshapes `suggestions/{service,repository,handlers}`; its docstring slice partner is T1 A-S2.
