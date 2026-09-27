---
name: "Chapter 10 — GitHub Actions schedule"
overview: "A crawl.yml workflow, modeled on openplz-import.yml, runs the crawler on a schedule and on demand, installing Playwright's browser and holding the crawler's API key as a repository secret."
todos:
  - id: workflow
    content: "crawl.yml with schedule and workflow_dispatch"
    status: pending
  - id: key
    content: "Issue the crawler's production API key and store it as a secret"
    status: pending
isProject: false
---

# Chapter 10 — GitHub Actions schedule

**Repo:** `redtape` (`.github/workflows`) · **Branch:** `feat/crawler-schedule` · **Status:** planned

**Depends on:** [9](09-run-orchestrator-and-report.md), auth [7](../../auth/chapters/07-api-key-model-and-hashing.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The crawler runs unattended on a schedule, exactly like the OpenPLZ import already does, without needing a
paid worker (program decision D3).

## Design decisions

**Modeled directly on
[openplz-import.yml](../../../.github/workflows/openplz-import.yml)**: `schedule` (weekly, not daily —
a discovery crawl over a small, curated source list does not need daily runs the way a location import
does; daily would also risk exceeding polite rate limits against the same handful of sites) plus
`workflow_dispatch` with a `sources` input (comma-separated, passed through to `--source`).

**Two jobs**: `lint-test` (reused from chapter 1's workflow via `workflow_call`, or duplicated inline if
that adds more complexity than it saves — decided during implementation by which reads more clearly) gates
the crawl job; `crawl` installs the package, runs `playwright install --with-deps chromium`, then
`python -m crawler.run --report-path report.json`, and uploads `report.json` as a workflow artifact
(`actions/upload-artifact`) so a run's outcome is inspectable without re-running it.

**Secrets**: `CRAWLER_API_KEY` (issued via auth's `issue_api_key.py --name crawler-prod`, chapter 7 of the
auth suite) and `API_BASE_URL` (the deployed Render URL) as repository secrets, following the same
"secrets live in GitHub, not `render.yaml`" pattern as `DATABASE_URL`.

**Failure visibility**: the job fails (non-zero exit, chapter 9) only on a source-level fetch failure, so a
red workflow run means "something is actually broken," not "a few duplicates were skipped" — matching the
"never silently fails" invariant without also being noisy.

## Files

| Path | Change |
| --- | --- |
| `.github/workflows/crawl.yml` | New |
| `docs/operations/scheduled-jobs.md` | Add the crawl job's entry, matching its existing table format |

## Red tests

| Check | Asserts |
| --- | --- |
| `workflow_dispatch` dry run | Manually triggered run with `sources` limited to the one real source completes and uploads a report |
| Scheduled trigger syntax | `act` or GitHub's workflow linter validates the YAML (no runtime assertion possible for `schedule`) |
| Secrets present | The job fails clearly (not with a confusing error) when `CRAWLER_API_KEY` is unset, verified once by temporarily unsetting it in a test run |

## Green

1. Workflow file, `workflow_dispatch` first (fastest to test manually).
2. Add `schedule`.
3. Artifact upload and the operations doc entry.
4. Manual dry run against production with `--dry-run` first, then a real limited run.

## Refactor gate

Workflow stays two jobs, no inline scripting beyond what `openplz-import.yml` already does at this
complexity. Report the outcome.

## Verification

Manual `workflow_dispatch` runs (dry-run, then a real limited run); inspect the uploaded report artifact.

## Out of scope

A second job runner (Actions is the only runtime here, D4), alerting beyond a failed workflow run turning
red in GitHub's UI.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-schedule
```

```text
feat(ci): add the scheduled crawl workflow
```
