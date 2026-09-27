---
name: "Chapter 10 — Web vote controls"
overview: "Up/down vote buttons and a score on suggestion cards and the detail page, working for signed-in users and prompting sign-in for anonymous visitors; the submitter sees a disabled state on their own suggestion."
todos:
  - id: api
    content: "voteApi.castVote and removeVote, useCastVote hook"
    status: pending
  - id: controls
    content: "VoteControls component with the four visual states"
    status: pending
isProject: false
---

# Chapter 10 — Web vote controls

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/voting-web-controls` · **Status:** planned

**Depends on:** [4](04-tally-and-thresholds.md), suggestion-interface [10](../../suggestion-interface/chapters/10-web-suggestion-list-and-detail.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Anyone signed in can vote directly from the suggestion card or detail page and immediately sees the updated
score; the four situations (not signed in, own suggestion, no vote yet, already voted) are each visually
distinct so nobody is confused about why a button is disabled.

## Design decisions

**One component, one decision function.** `components/VoteControls.tsx` (in
`apps/web/src/features/suggestions/`, alongside the existing suggestion components) renders from a pure
`voteControlsState(auth, suggestion) -> "signed_out" | "own_suggestion" | "can_vote" | "voted_up" |
"voted_down"`, tested standalone — the same "small pure decision function behind a component" shape as
auth's `RequireAuth` (chapter 11 there).

| State | Rendering |
| --- | --- |
| `signed_out` | Both buttons present, disabled-looking but clickable; click navigates to `/login` (not a dead control, an explicit invite) |
| `own_suggestion` | Both buttons disabled, tooltip explains why |
| `can_vote` | Both buttons enabled, neither highlighted |
| `voted_up` / `voted_down` | The matching button highlighted, both still clickable (clicking the highlighted one removes the vote — a toggle, not a one-way action) |

**Optimistic update, then reconcile.** `useCastVote` (TanStack Query mutation) optimistically updates the
cached score and `my_vote` before the request resolves, and rolls back on error — the score must feel
instant since it is the whole point of voting; the query key includes the suggestion id so only that one
card/detail re-renders.

**Card and detail share the component**; `SuggestionCard` gets a compact variant (`size="sm"`), the detail
page the full one — one component, a size prop, not two implementations (rule of three not yet met with
just two call sites, but a size variant costs nothing here and avoids near-duplication).

**i18n**: `vote.upvote`, `vote.downvote`, `vote.own_suggestion_tooltip`, `vote.sign_in_to_vote`.

## Files

**Add** — `apps/web/src/features/suggestions/{services/voteApi.ts, hooks/useCastVote.ts,
components/VoteControls.tsx, utils/voteControlsState.ts}`, tests beside each.

**Edit** — `apps/web/src/features/suggestions/components/suggestions-list/SuggestionCard.tsx`,
`apps/web/src/features/suggestions/components/suggestion-detail/SuggestionDetailView.tsx`,
`apps/web/src/i18n/fallback/{de,en}.json`, `apps/api/scripts/seed_data/translations/{de,en}.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `voteControlsState · signed out` | Returns `signed_out` |
| `voteControlsState · the submitter viewing their own suggestion` | Returns `own_suggestion` |
| `voteControlsState · signed in, no vote yet` | Returns `can_vote` |
| `voteControlsState · signed in, already up-voted` | Returns `voted_up` |
| `VoteControls · signed-out click navigates to /login` | Router assertion |
| `VoteControls · own_suggestion disables both buttons with a tooltip` | Accessible name/description |
| `VoteControls · clicking up-vote calls the API with value 1` | Request body |
| `VoteControls · clicking the already-active button removes the vote` | `DELETE` called |
| `VoteControls · updates the visible score before the request resolves` | Optimistic |
| `VoteControls · rolls back the score if the request fails` | Error path |
| `SuggestionCard · renders the compact VoteControls` | Present |
| `SuggestionDetailView · renders the full VoteControls` | Present |
| `i18n · every vote.* key exists in both fallback bundles` | Parity |

## Green

1. `voteControlsState`; tests 1–4.
2. API service and hook, happy path; tests 7–8.
3. Optimistic update and rollback; tests 9–10.
4. Component states and navigation; tests 5–6.
5. Card and detail integration; tests 11–12.
6. i18n; test 13.

## Refactor gate

`VoteControls` ≤ ~80 LOC by keeping the state decision and the mutation in their own files; the component
only renders and dispatches. Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/suggestions
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: vote up, vote down, unvote, try voting on your own suggestion, try voting while signed out.

## Out of scope

Moderator controls (chapter 11), the events/audit view.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-web-controls
```

```text
test(web): describe vote control states and optimistic voting

feat(web): add vote buttons to the suggestion card and detail page
```
