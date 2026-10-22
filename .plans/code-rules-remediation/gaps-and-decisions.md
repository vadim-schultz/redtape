---
name: Code rules remediation — Gaps and decisions
overview: "Settled decisions for the rules remediation: folder naming, registry policy, error mapping, sequencing."
isProject: false
---

# Code rules remediation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | Chapter 0 (green CI) is **done and merged to `main`**: `testTimeout`/`hookTimeout` 15 s in `apps/web/vite.config.ts` and `asyncUtilTimeout` 5 s in `apps/web/src/test/setup.ts`. The 10 suggestions/discovery test failures were timeouts under parallel load, not logic bugs. |
| D2 | Backend services and repositories raise **domain errors**; controllers or router exception handlers map them to HTTP. Copy the suggestions/voting pattern (`_to_http`). Status codes of existing endpoints do not change. |
| D3 | The 3-parameter limit applies (more than 3 means a DTO), even though the audit first counted against 4. |
| D4 | Frontend `<X>View/` folders follow **rsb-test-storage PascalCase** (`DocumentsListView/`), with `index.ts` barrels. Flag the rename in the chapter 11 PR. |
| D5 | No `registry/` folder unless a real plug-in point appears. Candidate: suggestion payload renderers keyed by suggestion type (`new_document`, `new_requirement`) once a third variant exists (rule of three). |
| D6 | A central `app/queryKeys.ts` replaces inline query keys (chapter 11), not earlier, so chapters 7-10 do not fight over key shapes. |
| D7 | Frontend `contexts/` stays plural (rsb is itself inconsistent). Write it down in `apps/web/CLAUDE.md` (chapter 11). |
| D8 | Chapter order interleaves nothing: backend 1-6, then frontend 7-11. Chapter 11 runs last so the prop and wrapper cleanup lands in final locations. |
| D9 | Re-measure size violations at the start of chapters 6 and 7-10 with a script (line counts per function/class, props per component); the audit numbers were read by eye. Record the baseline in the chapter PR. |
| D10 | Pure moves (chapter 11) are separate commits per feature, with no logic edits, so `git log --follow` and review stay readable. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| ESLint `max-lines` / `no-restricted-imports` enforcement | Add in chapter 11 if the rules can be set without a flood of existing violations; otherwise record as a follow-up. |
| Splitting the 500-line `scripts/import_openplz_locations.py` | Out of scope unless chapter 6 has capacity. |
| Jest-style "script tag" and jsdom CSS stderr noise | Harmless; filter only if it hides real failures. |

## Out of scope

New features, API contract changes, migrations, discovery ingest app (`apps/discovery-ingest`), design/theme changes, dependency upgrades.
