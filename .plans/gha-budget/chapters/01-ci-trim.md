---
name: "Chapter 1 — CI trim"
overview: "Cancel superseded pull request CI runs and drop the non-existent develop branch from push triggers, so a push-heavy chapter loop stops paying for runs nobody reads."
todos:
  - id: concurrency
    content: "Add a per-ref concurrency group to the three CI workflows"
    status: pending
  - id: triggers
    content: "Remove develop from push branches"
    status: pending
isProject: false
---

# Chapter 1 — CI trim

**Repo:** `redtape` (`.github/workflows`) · **Branch:** `chore/gha-budget-ci-trim` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

API CI (255 min) and web CI (200 min) were 56% of October's spend. Every push to a pull request starts a new run while the previous one keeps running to completion. Cancelling the superseded run saves the full cost of every overlapped push.

## Design

In `api-lint-test.yml`, `web-ci.yml` and `discovery-ingest-ci.yml`, add at workflow level (between `on:` and `defaults:`/`jobs:`):

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

`cancel-in-progress` is true only for pull requests. A push to `main` is never cancelled by the next one.

In the same three files, change `push.branches` from `[main, develop]` to `[main]`. `git branch -r` shows no `develop` branch; confirm that before editing and say so in the PR body.

Do **not** change: the separate `migrations` job (deliberate, commit e84cd70), `npm install` in the web workflow (documented `npm ci` flakiness), action versions, or any step.

## Tests

No unit harness. Gate: actionlint clean on all three files (rollout invariant 2). Also confirm `git diff` touches only the `concurrency` and `push.branches` lines.

## Refactor gate

Three identical 3-line blocks across three files are acceptable (workflow files cannot share YAML blocks without a reusable workflow, which would be a new moving part). Record "audited, nothing needed".

## Commits

- `ci: cancel superseded pull request runs`
- `ci: stop triggering push CI for the absent develop branch`

## Verification (deferred)

First live proof after the quota resets: push two commits quickly to a PR and see the first run `cancelled` (operator step O4 in chapter 6).
