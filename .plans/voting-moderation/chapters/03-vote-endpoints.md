---
name: "Chapter 3 — Vote endpoints"
overview: "PUT and DELETE /api/v1/suggestions/{id}/vote for signed-in users, mapping the service's rule errors to 401/403/404/409."
todos:
  - id: controller
    content: "VotingController with put and delete handlers"
    status: done
isProject: false
---

# Chapter 3 — Vote endpoints

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-endpoints` · **Status:** implemented, PR open

**Depends on:** [2](02-cast-vote-service.md), auth [4](../../auth/chapters/04-current-user-dependency.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A signed-in person can vote and unvote over HTTP.

## Design decisions

**Route** under the suggestions path, own feature (`features/voting/{router,controller}.py`), same pattern
as evidence's sub-route: `/api/v1/suggestions/{suggestion_id}/vote`.

**`current_user` only** (human; D2's self-vote rule presumes a human submitter and voter — crawlers never
vote, this is not even a `principal` route).

**Error mapping**: `SelfVoteError` → 403 (`{"detail": "Cannot vote on your own suggestion"}`);
`SuggestionNotVotableError` → 409; `NotFoundError` → 404; validation of `value` (must be exactly `1` or
`-1`) → 422 before the service is called at all.

**`PUT` returns the updated tally-free suggestion state** is deferred: this chapter's response is just
`{"ok": true}` plus the vote's own `value`; the fuller `SuggestionRead` with `tally`/`my_vote` is chapter
4's job, so this chapter's tests do not assert tally shape.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/voting/controller.py`, `router.py` | Handlers |
| `apps/api/app/main.py` | Register `voting_router` |
| `apps/api/tests/test_vote_endpoints.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `PUT .../vote · records an up-vote and returns it` | 200, `value: 1` |
| `PUT .../vote · records a down-vote` | 200, `value: -1` |
| `PUT .../vote · rejects a value other than 1 or -1` | 422 |
| `PUT .../vote · returns 401 without a token` | Negative |
| `PUT .../vote · returns 403 for the suggestion's own submitter` | Mapped from `SelfVoteError` |
| `PUT .../vote · returns 409 for a non-pending suggestion` | Mapped |
| `PUT .../vote · returns 404 for an unknown suggestion` | Mapped |
| `DELETE .../vote · removes an existing vote` | 204 |
| `DELETE .../vote · is a no-op when there is no vote` | 204, not an error |
| `DELETE .../vote · returns 401 without a token` | Negative |

## Green

1. `PUT` happy path and validation; tests 1–4.
2. Error mapping; tests 5–7.
3. `DELETE`; tests 8–10.

## Refactor gate

Handlers ≈5 LOC each; shared error-mapping dict with chapters 5/6's controllers where the error types
overlap. Report the outcome.

**Outcome:** `cast` is 4 LOC of body (try/except/return), `remove` is 1 LOC; both within budget, no nesting
past one level. Error mapping follows the suggestions controller's existing `_STATUS_BY_ERROR`-dict pattern
(here `VOTE_ERROR_STATUS`) rather than a chain of `isinstance` checks, so it is a plain, importable dict —
chapters 5/6 don't exist yet (not yet on this branch), so there's nothing to share with today; when their
controllers land, merging into one dict is a small edit, not a redesign.

## Verification

```bash
cd apps/api
python -m pytest tests/test_vote_endpoints.py
cd ../.. && ./ci.sh
curl -s -X PUT "localhost:8000/api/v1/suggestions/$ID/vote" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"value": 1}'
```

## Out of scope

Tally in the response (chapter 4), transitions (chapter 5).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-endpoints
```

```text
test(api): describe vote and unvote over HTTP, and their errors

feat(api): add PUT and DELETE /api/v1/suggestions/{id}/vote
```
