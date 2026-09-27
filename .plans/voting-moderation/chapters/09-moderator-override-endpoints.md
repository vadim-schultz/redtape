---
name: "Chapter 9 — Moderator override endpoints"
overview: "POST .../approve and .../reject let a moderator decide a suggestion directly, through the same transition_to used by the threshold path, and GET .../events exposes the audit trail."
todos:
  - id: controller
    content: "Override handlers guarded by require_role(moderator)"
    status: pending
  - id: reason
    content: "Optional reason on rejection, recorded as a moderator_override event"
    status: pending
isProject: false
---

# Chapter 9 — Moderator override endpoints

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-moderator-override` · **Status:** planned

**Depends on:** [8](08-suggestion-event-log.md), auth [6](../../auth/chapters/06-role-guards.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5, §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A moderator can resolve a suggestion without waiting on votes, and anyone with the role can review why
past decisions were made (D6).

## Design decisions

**Same entry point as the threshold path** (D6): both handlers call `suggestions_service.transition_to(id,
"approved" | "rejected", actor=current_user, reason=...)`. `transition_to` gains an optional `reason` and
records `event_type="moderator_override"` (not `"status_changed"`) **when an actor is present**, so the
event log always distinguishes "the crowd decided" from "a moderator decided" without a second code path
for the transition itself — same guard method (`AlreadyDecidedError`), same promotion call.

**`require_role(UserRole.moderator)`** guard (auth chapter 6) on both write handlers; `GET .../events` is
moderator-only too, since events are not shown on the public suggestion detail (a submitter's identity
could otherwise leak through raw event data).

**`reject` takes an optional `reason`**, stored in the event's `data`, never on the suggestion itself (no
schema change to `suggestion` for this) — visible only through the events endpoint.

**Overriding an already-decided suggestion** returns 409 (`AlreadyDecidedError`, same mapping as any other
transition conflict) — a moderator cannot "re-decide" here either (matches the open seam: reopening needs a
new suggestion).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/service.py` | `transition_to(reason=...)`, override event type |
| `apps/api/app/features/voting/controller.py` | `POST .../approve`, `POST .../reject`, `GET .../events` |
| `apps/api/app/schema/events/read.py` | `EventRead` |
| `apps/api/tests/test_moderator_override.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST .../approve · a moderator approves a pending suggestion and it promotes` | Status, created row |
| `POST .../reject · a moderator rejects with a reason` | Status, event has the reason |
| `POST .../approve · a plain user gets 403` | Role guard |
| `POST .../approve · anonymous gets 401` | Guard order |
| `POST .../approve · an already-decided suggestion gets 409` | `AlreadyDecidedError` |
| `POST .../reject · without a reason still succeeds` | Optional field |
| `transition_to · a moderator override logs moderator_override, not status_changed` | Event type distinguishes source |
| `GET .../events · a moderator sees the full trace` | Includes submitted, voted, status_changed/moderator_override |
| `GET .../events · a plain user gets 403` | Role guard |
| `GET .../events · events never include emails or key hashes` | Negative, string search |

## Green

1. `transition_to(reason=...)` and event-type distinction; tests 1, 2, 7.
2. Guards; tests 3–5.
3. Optional reason; test 6.
4. `GET .../events`; tests 8–10.

## Refactor gate

Both override handlers share one ≈5 LOC body parameterized by target status (a small
`_override(id, status, actor, reason)` helper), not duplicated logic. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_moderator_override.py
cd ../.. && ./ci.sh
curl -s -X POST "localhost:8000/api/v1/suggestions/$ID/reject" -H "Authorization: Bearer $MOD_TOKEN" \
  -H 'Content-Type: application/json' -d '{"reason": "Duplicate of an existing document"}'
```

## Out of scope

Web moderation UI (chapter 11).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-moderator-override
```

```text
test(api): describe moderator overrides and the events endpoint

feat(api): add approve, reject and events endpoints for moderators
```
