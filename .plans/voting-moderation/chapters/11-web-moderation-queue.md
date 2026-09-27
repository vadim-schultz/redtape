---
name: "Chapter 11 — Web moderation queue"
overview: "A /moderation page, moderator-only, listing pending suggestions with one-click approve and reject (with an optional reason), and an events timeline per suggestion for dispute resolution."
todos:
  - id: page
    content: "ModerationQueuePage reusing the suggestions list with actions"
    status: pending
  - id: events
    content: "EventsTimeline component"
    status: pending
isProject: false
---

# Chapter 11 — Web moderation queue

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/voting-web-moderation` · **Status:** planned

**Depends on:** [9](09-moderator-override-endpoints.md), auth [11](../../auth/chapters/11-web-menu-and-route-guard.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A moderator has one page to work through the pending queue: see each suggestion, its votes, decide, and
check the history if something is disputed.

## Design decisions

**Route `/moderation`**, `<RequireAuth minRole="moderator">` (auth chapter 11 already supports this prop).
Menu gains a **Moderation** entry, visible only when `role === "moderator" || role === "admin"` (read from
the same `/me` result the account menu item already uses).

**Reuses the suggestions list, does not fork it.** `ModerationQueuePage` renders
`SuggestionsListPage`'s underlying list view (suggestion-interface chapter 10) with `status=pending` fixed
and an extra `actions` slot rendered per card (`ModeratorActions`: approve button, reject button opening a
small reason dialog) — passed as a render prop/slot, so the public list component gains one optional prop,
not a duplicate page.

**`ModeratorActions`** calls the approve/reject mutations, then invalidates the suggestions list query so
the decided item drops out of the pending queue immediately (no manual removal from local state — trust the
refetch, matching the pattern of every other list in this codebase).

**Reject reason dialog**: a small Chakra `Dialog` with an optional textarea; submitting with it empty is
allowed (reason is optional per the API, chapter 9).

**`EventsTimeline`** component on the suggestion detail page, visible only to moderators (conditionally
rendered, same role check as the menu item): fetches `GET .../events` and renders each as one line
(`icon, type, actor or "automatic", relative time`), oldest first.

**i18n**: `moderation.*` keys (`queue_title`, `approve`, `reject`, `reject_reason_placeholder`,
`no_pending`), `events.*` keys per event type label.

## Files

**Add** — `apps/web/src/features/moderation/{containers/ModerationQueuePage.tsx,
components/ModeratorActions.tsx, components/RejectReasonDialog.tsx, components/EventsTimeline.tsx,
hooks/useModeratorDecision.ts, hooks/useSuggestionEventsQuery.ts, services/eventsApi.ts}`, tests beside each.

**Edit** — `apps/web/src/app/routes.tsx`, `apps/web/src/components/layout/AppMenu.tsx`,
`apps/web/src/features/suggestions/containers/SuggestionsListPage.tsx` (optional `renderActions` slot),
`apps/web/src/features/suggestions/containers/SuggestionDetailPage.tsx` (conditional `EventsTimeline`),
`apps/web/src/i18n/fallback/{de,en}.json`, `apps/api/scripts/seed_data/translations/{de,en}.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `routes · /moderation is redirected for a non-moderator` | Guard via `RequireAuth minRole` |
| `AppMenu · Moderation is hidden for a plain user` | Negative |
| `AppMenu · Moderation is visible for a moderator` | Positive |
| `ModerationQueuePage · lists pending suggestions with approve and reject actions` | Actions rendered |
| `ModeratorActions · approve calls the endpoint and the item leaves the list` | Refetch removes it |
| `ModeratorActions · reject without a reason succeeds` | Optional field |
| `ModeratorActions · reject with a reason includes it in the request` | Body |
| `RejectReasonDialog · Escape closes without submitting` | Keyboard |
| `EventsTimeline · renders submitted, voted and status_changed events in order` | Order and labels |
| `EventsTimeline · shows the actor's name or "Automatic" when none` | Both cases |
| `EventsTimeline · is not rendered for a non-moderator viewer` | Negative |
| `i18n · every moderation.* and events.* key exists in both fallback bundles` | Parity |

## Green

1. Route, guard, menu visibility; tests 1–3.
2. Queue page with actions; tests 4–7.
3. Reject dialog; test 8.
4. Events timeline; tests 9–11.
5. i18n; test 12.

## Refactor gate

`ModerationQueuePage` composes the existing list view plus `ModeratorActions`; it does not re-implement
filtering or pagination. Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/moderation src/features/suggestions src/components/layout
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: as a moderator, approve one suggestion and reject another with a reason; check its events timeline;
confirm a plain user cannot reach `/moderation`.

## Out of scope

Bulk actions, filtering the queue by jurisdiction, notifications to the submitter.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-web-moderation
```

```text
test(web): describe the moderation queue, its actions and the events timeline

feat(web): add the moderator queue page and per-suggestion event history
```
