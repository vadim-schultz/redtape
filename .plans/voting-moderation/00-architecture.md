---
name: Voting Moderation — Architecture
overview: "Signed-in users vote on pending suggestions; crossing a threshold moves a suggestion to approved or rejected; approval promotes new_document and new_requirement suggestions into the real catalogue; every status change is recorded in an append-only event log; moderators can override."
isProject: false
---

# Voting Moderation — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

[suggestion-interface](../suggestion-interface/00-architecture.md) can create and read suggestions but every
one stays `pending` forever (program decision D4: suggestions-only). This suite is the missing half: how a
`pending` suggestion becomes part of the catalogue, or is turned away, and who decided. It answers the
`crawlers-jobs`/`social-moderation` strand's TBD child plans
(`01-proposal-state-machine.md`, `02-voting-and-thresholds.md`, `03-audit-log-schema.md`,
`04-moderator-workflows.md`) using this program's vocabulary (**suggestion**, not "proposal";
see the docs-sync chapter for reconciling names).

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Vote** | One user's up or down on one suggestion. A user has at most one vote per suggestion. |
| **Tally** | `{up, down, score}` derived from votes; `score = up - down`. |
| **Threshold** | The score at which a suggestion auto-approves or auto-rejects. |
| **Promotion** | Turning an `approved` `new_document` or `new_requirement` suggestion into real `Document`/`DocumentRequirement` rows. |
| **Override** | A moderator setting status directly, bypassing the vote threshold. |
| **Event** | One immutable row recording a status change or vote, for audit and dispute resolution. |

## 3. Data model

**`suggestion_vote`** — `id` UUID, `suggestion_id` FK `ondelete=CASCADE`, `user_id` FK `app_user.id`
`ondelete=CASCADE`, `value` `SmallInteger` constrained to `{-1, 1}`, `created_at`. `uq_suggestion_vote_user`
unique on (`suggestion_id`, `user_id`) — one vote per user per suggestion, changed by upsert, not by a
second row.

**`suggestion_event`** — `id` UUID, `suggestion_id` FK `ondelete=CASCADE`, `event_type` native enum
(`submitted`, `voted`, `status_changed`, `promoted`, `moderator_override`), `actor_user_id` nullable FK,
`actor_api_key_id` nullable FK, `data` JSONB (event-specific: `{value}` for a vote, `{from, to, reason?}`
for a status change), `created_at`. Append-only: no update or delete path exists anywhere in the code.

**No new column on `suggestion`** for the tally — it is computed (§5), so the source of truth is always the
vote rows, never a cached counter that can drift.

## 4. Threshold

`Settings.vote_approve_threshold` (default 3) and `vote_reject_threshold` (default -3), symmetric integers.
`score >= approve_threshold` → `approved`; `score <= reject_threshold` → `rejected`; otherwise `pending`.
Evaluated synchronously after every vote write (no scheduled job): the vote that crosses the line also
triggers the transition, in the same request.

## 5. API contract

| Route | Auth | Purpose |
| --- | --- | --- |
| `PUT /api/v1/suggestions/{id}/vote` | user | Body `{value: 1 \| -1}`; upsert; may trigger a transition |
| `DELETE /api/v1/suggestions/{id}/vote` | user | Remove the caller's vote |
| `GET /api/v1/suggestions/{id}` (extended) | public | Gains `tally {up, down, score}` and, if authenticated, `my_vote` |
| `POST /api/v1/suggestions/{id}/approve` | moderator | Override to `approved`; promotes |
| `POST /api/v1/suggestions/{id}/reject` | moderator | Override to `rejected`; body `{reason?}` |
| `GET /api/v1/suggestions/{id}/events` | moderator | Audit trail for one suggestion |

Errors: 401, 403 (non-moderator override), 404, 409 (voting or overriding a suggestion that is no longer
`pending`).

## 6. Promotion

A `SuggestionPromoter` service, invoked exactly when status becomes `approved` (by threshold or override),
dispatches on kind (reusing the [suggestion-interface kind-handler](../suggestion-interface/chapters/08-requirement-edge-kind.md)
pattern): `new_document` creates a `Document` via `DocumentService.create_from_suggestion(...)` (a new,
additive method — the read-only service gains its first write); `new_requirement` creates a
`DocumentRequirement` the same way. Promotion is idempotent: it is invoked once, inside the same transaction
as the status change, and recorded as a `promoted` event carrying the created id, so a retry (there is none
today, but the design does not preclude one) could check the event log first.

## 7. Layering

`features/voting/{router,controller,service,repository,dependencies}.py` for votes and the event log;
promotion lives in `features/suggestions/promotion.py` since it is fundamentally a suggestions concern that
happens to be triggered by voting — voting's service calls
`suggestions_service.transition_to(suggestion_id, new_status, actor, reason=None)`, which performs the
transition, promotion (if approved) and event logging as one unit, so voting never touches
`document`/`document_requirement` directly.

## 8. Web

Suggestion list and detail pages (suggestion-interface) gain vote buttons and a tally; a `/moderation` page,
protected by `RequireAuth minRole="moderator"`, lists pending suggestions with approve/reject actions and a
link to each one's events.

## 9. Out of scope

Vote weighting or reputation, vote decay over time, comments/discussion threads, notifications on status
change, undoing a promotion, the `ui_translation` community-review idea in the strand doc (explicitly
"future" there).
