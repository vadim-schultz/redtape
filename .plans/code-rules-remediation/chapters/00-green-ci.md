---
name: "Chapter 0 — Green CI"
overview: "Raise web test timeouts so the full parallel vitest run passes; get ./ci.sh to exit 0. Done."
isProject: false
---

# Chapter 0 — Green CI

**Repo:** `redtape` · **Branch:** `fix/web-test-timeouts` · **Status:** **done** (landed on `main`; not part of the chief-of-staff run)

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## What was done

- Red: the full `npm test` showed 10 failures: `SuggestPage.test.tsx` (4), `SuggestionForm.test.tsx` (5), and one `routes.discoveryAdmin.test.tsx` case. Each file passed in isolation, so the cause was the 5000 ms test timeout and the 1000 ms Testing Library `waitFor` default under parallel load (each Chakra select interaction costs about 1 s).
- Green: `apps/web/vite.config.ts` `test:` block got `testTimeout: 15000` and `hookTimeout: 15000`; `apps/web/src/test/setup.ts` got `configure({ asyncUtilTimeout: 5000 })`. Full suite: 85 files, 336 tests passed.
- `./ci.sh` exited 0 end to end ("All CI checks passed!").

## Notes for later chapters

- The "script tag" and "Could not parse CSS stylesheet" stderr lines come from jsdom and Chakra/emotion; they are harmless.
- If a later chapter adds slow interaction tests, prefer a shared helper over raising the timeouts again.
