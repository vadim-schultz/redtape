---
name: "Chapter 10 — Web login UI"
overview: "A /login page with an email magic-link form, sent-state and error handling, translated in de and en, replacing the unused password-era auth keys."
todos:
  - id: page
    content: "LoginPage container and LoginForm component"
    status: pending
  - id: i18n
    content: "auth.* keys in seeds and fallback bundles"
    status: pending
  - id: route
    content: "/login route, redirect when already signed in"
    status: pending
isProject: false
---

# Chapter 10 — Web login UI

**Repo:** `redtape` (`apps/web`, i18n seeds in `apps/api/scripts/seed_data/translations`) · **Branch:** `feat/auth-web-login` · **Status:** planned

**Depends on:** [9](09-web-supabase-session.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A person can request a magic link at `/login`, sees a clear "check your inbox" state, and lands back in the
app signed in. Unconfigured environments show a friendly "sign-in unavailable" message instead of a form.

## Design decisions

**Component layout (one per file, tree mirrors hierarchy):**

```
containers/LoginPage.tsx            (state: idle | sending | sent | error; redirect if authenticated)
components/login/LoginForm.tsx      (email field + submit)
components/login/LoginSentNotice.tsx
components/login/LoginErrorNotice.tsx
```

**Validation is local and minimal**: a non-empty string containing `@`; the server (Supabase) is the real
validator. The submit button is disabled while sending.

**Redirect target.** `emailRedirectTo` is `${window.location.origin}/login`; on return, the context sees the
session and `LoginPage` navigates to the `from` location kept in router state, defaulting to `/documents`.

**i18n.** New keys: `auth.email_placeholder`, `auth.send_link`, `auth.link_sent_title`, `auth.link_sent_body`,
`auth.error_generic`, `auth.unavailable`. The unused `auth.password` key is removed from
`seed_data/translations/{de,en}.json` and `apps/web/src/i18n/fallback/{de,en}.json`; the fallback test
(`fallback.test.ts`) already checks bundle parity, and seeds stay idempotent.

**No email enumeration.** The "link sent" message is shown whether or not the address has an account
(Supabase behaves the same way with sign-ups enabled).

**Not in the menu yet.** The page is reachable by URL only until chapter 11, so this chapter ships without
changing existing screens.

## Files

**Add** — `apps/web/src/features/auth/containers/LoginPage.tsx`, `apps/web/src/features/auth/components/login/*`,
tests beside them.

**Edit** — `apps/web/src/app/routes.tsx` (lazy `/login`), `apps/web/src/i18n/fallback/{de,en}.json`,
`apps/api/scripts/seed_data/translations/{de,en}.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `LoginForm · submits the entered email to the gateway` | Fake gateway receives it |
| `LoginForm · rejects an empty email without calling the gateway` | Negative |
| `LoginForm · rejects a value without an @` | Negative |
| `LoginForm · disables the button while sending` | State |
| `LoginPage · shows the sent notice after a successful request` | Text visible |
| `LoginPage · shows the error notice when the gateway fails` | And the form stays usable |
| `LoginPage · shows the unavailable message when auth is unconfigured` | No form rendered |
| `LoginPage · redirects to the originating page once authenticated` | Router state `from` |
| `LoginPage · redirects to /documents when there is no origin` | Default |
| `i18n · every auth.* key exists in both fallback bundles` | Parity |
| `i18n · auth.password no longer exists` | Removal |

## Green

1. Form and validation; tests 1–4.
2. Page states; tests 5–7.
3. Redirects; tests 8–9.
4. Keys in fallback and seeds; tests 10–11.

## Refactor gate

- Page holds state only; markup lives in the three notices/form components (each ≤ ~60 LOC).
- Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/auth src/i18n
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
cd apps/api && python scripts/seed_i18n.py   # idempotent, run twice
```

Manual (Supabase configured): request a link, open it, arrive signed in; repeat in `de`; with variables
removed the page shows the unavailable message.

## Out of scope

Menu entry and protected routes (chapter 11), OAuth buttons, password reset.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-web-login
```

```text
test(web): describe magic-link login states and redirects

feat(web): add login page with email magic link and translations
```
