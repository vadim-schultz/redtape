---
name: "Chapter 9 — Web Supabase session"
overview: "An authGateway wrapping supabase-js behind our own interface, an AuthContext exposing session state, and apiRequest/useApi sending the bearer token when signed in; no visible UI yet."
todos:
  - id: gateway
    content: "authGateway interface, supabase implementation, in-memory fake"
    status: completed
  - id: context
    content: "AuthContext and AuthProvider mounted in AppBootstrap"
    status: completed
  - id: api
    content: "apiRequest accessToken option; useApi supplies it"
    status: completed
isProject: false
---

# Chapter 9 — Web Supabase session

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/auth-web-session` · **Status:** done

**Depends on:** [4](04-current-user-dependency.md), [5](05-me-endpoint.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7–8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The web app can hold a Supabase session and attach `Authorization: Bearer …` to API calls. Nothing
user-visible changes: with no `VITE_SUPABASE_*` variables the gateway reports "not configured" and the app
behaves as today.

## Design decisions

**We own the seam, not Supabase.** `features/auth/services/authGateway.ts` defines
`AuthGateway { getSession, onChange(cb) → unsubscribe, signInWithEmail(email), signOut }` with our own
`AuthSession { accessToken, userId, email }`. `supabaseAuthGateway.ts` is the only file importing
`@supabase/supabase-js`. Tests use `createFakeAuthGateway()`; the Supabase library is never mocked
(tdd-workflow: do not mock what you do not own).

**Context shape**: `{ status: "loading" | "anonymous" | "authenticated" | "unconfigured", session, user, signIn, signOut }`.
`user` is loaded once from `GET /api/v1/me` through TanStack Query when authenticated, so the UI has the
local role.

**Token flow.** `apiRequest` gets an optional `accessToken`; when present it adds the `Authorization`
header (existing option spread stays last so callers can still override). `useApi` reads the token from
`AuthContext`, keeping call sites unchanged.

**Proxy is verified, not assumed.** A worker test asserts `buildUpstreamRequest` keeps the `Authorization`
header (the proxy strips only `host` and `origin`).

**Query keys** that depend on identity (`/me`, later `my_vote`) include the user id, and the provider clears
the query cache on sign-out, so a second person on the same browser never sees the first person's data.

**Config**: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` documented in `apps/web/.env.example` (created if
missing). Dependency: `@supabase/supabase-js` in `package.json`; the lockfile check in `ci.sh` (registry
URLs) must pass.

## Files

**Add** — `apps/web/src/features/auth/services/authGateway.ts`, `supabaseAuthGateway.ts`, `fakeAuthGateway.ts`
(test support), `apps/web/src/features/auth/contexts/AuthContext.tsx`, `apps/web/src/features/auth/hooks/useMe.ts`,
`apps/web/src/features/auth/services/authApi.ts` (`fetchMe`).

**Edit** — `apps/web/src/services/api.ts`, `apps/web/src/app/AppBootstrap.tsx` (mount provider),
`apps/web/src/test/renderWithProviders.tsx` (optional fake gateway), `apps/web/package.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `AuthProvider · status is unconfigured when the gateway is not configured` | No Supabase vars |
| `AuthProvider · status becomes authenticated when the gateway has a session` | Fake with session |
| `AuthProvider · status becomes anonymous after sign-out` | Change event |
| `AuthProvider · sign-out clears cached queries` | Cache empty afterwards |
| `useMe · fetches /me only when authenticated` | No request while anonymous |
| `apiRequest · adds the bearer header when an access token is given` | Header value |
| `apiRequest · sends no Authorization header without a token` | Negative |
| `useApi · attaches the current session token` | Through provider |
| `proxyApi · forwards the Authorization header upstream` | Worker test |
| `proxyApi · still strips host and origin` | Regression guard |

## Green

1. Gateway interface and fake; context with statuses; tests 1–3.
2. `apiRequest` token option; tests 6–7.
3. `useApi`, `useMe`, cache clearing; tests 4, 5, 8.
4. Worker tests 9–10 (no code change expected).
5. Real Supabase gateway (thin; covered by manual check).

## Refactor gate

- One component/hook per file; `AuthContext` ≤ ~100 LOC (state reducer extracted if it grows).
- `supabaseAuthGateway.ts` maps library shapes to `AuthSession` in one function.
- Report the outcome.

✅ `AuthContext.tsx` came in at 95 lines: one `useEffect` subscribing to `getSession()` + `onChange`, one
`useMe` call, two `useCallback`-wrapped actions, one `useMemo`d value — no branch count or nesting depth
crossed the rule-of-three trigger, so no reducer extraction. `supabaseAuthGateway.ts` maps the Supabase
`Session` to `AuthSession` in the single `toAuthSession` function as planned, and stayed the only file
importing `@supabase/supabase-js`. One deviation from the sketch: `useMe` keys off `userId` (matching the
"query keys include the user id" decision) rather than `accessToken`, so it takes `(accessToken, userId)`
instead of the session object — kept the two params instead of threading the whole `AuthSession` through to
avoid an unused-field coupling.

## Verification

```bash
cd apps/web
npm run test -- src/features/auth src/services src/worker
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: with real Supabase variables in `.env.local`, sign in through the browser console gateway call and
see `/me` succeed in the network tab (UI arrives in chapter 10).

## Out of scope

Login form (chapter 10), menu entry and guards (chapter 11), token refresh logic beyond the library's.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-web-session
```

```text
test(web): describe auth session state and bearer token propagation

feat(web): add auth gateway, AuthContext and token-aware apiRequest
```
