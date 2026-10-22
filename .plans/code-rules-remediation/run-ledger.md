# Code rules remediation — Run ledger

**Loop branch:** `feat/plans-code-rules-remediation`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 0. Green CI | `fix/web-test-timeouts`, landed directly on `main` at operator request | 10 web tests red under the full parallel run (SuggestPage x4, SuggestionForm x5, one discovery-admin route test) → 336/336 green after `testTimeout`/`hookTimeout` 15 s and `asyncUtilTimeout` 5 s | n/a (test config only) | local `./ci.sh` exit 0 ("All CI checks passed!"); API, migrations, web lint/typecheck/test/build, discovery skills, discovery-ingest all green | **done** |

## Release gate

- [x] Chapter 0 done; `./ci.sh` green on `main`.
- [ ] Chapters 1-11 recorded with red → green evidence and refactor outcome.
- [ ] `./ci.sh` passes on `feat/plans-code-rules-remediation`.
- [ ] Size re-measure shows no class over about 100 lines and no component over 3 props in the touched features (or each exception is recorded here).
- [ ] Release PR opened from `feat/plans-code-rules-remediation` to `main`.
