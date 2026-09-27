---
name: "Chapter 11 — Web menu and route guard"
overview: "The floating menu shows Sign in or the user's email with Sign out, and a RequireAuth wrapper protects routes by redirecting anonymous visitors to /login while remembering where they were going."
todos:
  - id: menu
    content: "AccountMenuItem in AppMenu"
    status: pending
  - id: guard
    content: "RequireAuth route wrapper"
    status: pending
isProject: false
---

# Chapter 11 — Web menu and route guard

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/auth-web-guard` · **Status:** planned

**Depends on:** [10](10-web-login-ui.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Signed-out visitors see **Sign in** in the burger menu; signed-in users see their email and **Sign out**.
Later suites wrap `/suggest` and `/moderation` in `RequireAuth` without redoing any auth work.

## Design decisions

**Extends the floating shell** ([floating-nav](../../floating-nav/00-architecture.md)): one new item at the
top of `AppMenu`, above the colour switch, separated by `Menu.Separator`. It is a separate component
`AccountMenuItem` (one per file, next to `LocaleSubmenu`); `AppMenu` only composes it.

**Hidden when unconfigured.** `status === "unconfigured"` renders nothing, so environments without Supabase
have no dead control (rollout invariant 2 and floating-nav "no dead UI").

**`RequireAuth`** takes `minRole?: "user" | "moderator"` (default `user`):

| Status | Result |
| --- | --- |
| `loading` | Renders nothing (page skeleton from the Suspense fallback stays) |
| `anonymous` | `<Navigate to="/login" state={{ from: location }} replace />` |
| `authenticated`, role sufficient | children |
| `authenticated`, role too low | A `ForbiddenView` (sibling of `NotFoundView`) |
| `unconfigured` | `NotFoundView` (the route effectively does not exist) |

**Role comes from `/me`** (chapter 9), never from the token; while `/me` is loading the guard treats the
state as `loading`.

**Sign-out** calls the gateway and navigates to `/documents` if the current route is protected.

## Files

**Add** — `apps/web/src/components/layout/AccountMenuItem.tsx`, `apps/web/src/features/auth/components/RequireAuth.tsx`,
`apps/web/src/views/ForbiddenView.tsx`, tests beside each.

**Edit** — `apps/web/src/components/layout/AppMenu.tsx`, `apps/web/src/i18n/fallback/{de,en}.json` and seeds
(`auth.sign_in`, `auth.sign_out`, `errors.forbidden_title`, `errors.forbidden_body`).

## Red tests

| Test | Asserts |
| --- | --- |
| `AccountMenuItem · anonymous shows Sign in linking to /login` | Role link |
| `AccountMenuItem · authenticated shows the email and Sign out` | Both visible |
| `AccountMenuItem · Sign out calls the gateway` | Fake records it |
| `AccountMenuItem · renders nothing when unconfigured` | Negative |
| `AppMenu · account item precedes the colour switch` | Order |
| `RequireAuth · anonymous is redirected to /login with the origin in state` | Navigation |
| `RequireAuth · authenticated user sees the children` | Happy |
| `RequireAuth · user below minRole sees the forbidden view` | Negative |
| `RequireAuth · moderator passes a moderator route` | Positive pair |
| `RequireAuth · unconfigured shows the not-found view` | Negative |
| `RequireAuth · renders nothing while status is loading` | No flash of redirect |

## Green

1. `AccountMenuItem` states; tests 1–4.
2. Mount in `AppMenu`; test 5.
3. `RequireAuth` states; tests 6–11.

## Refactor gate

- `RequireAuth` decision is a small pure function `guardOutcome(status, role, minRole)` returning
  `"wait" | "login" | "allow" | "forbidden" | "hidden"`, so the component is a switch over a tested value
  (five outcomes: dispatch, not an if-chain).
- Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout src/features/auth src/views
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: signed out → menu shows Sign in; sign in → email and Sign out; unset Supabase variables → no account
item. Keyboard: the item is reachable and Escape returns focus to the burger.

## Out of scope

Actual protected pages (suggestion and moderation suites), avatar, profile page.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-web-guard
```

```text
test(web): describe account menu item and route guard outcomes

feat(web): add account menu item and RequireAuth
```
