# Run ledger

**Loop branch:** `feat/plans-discovery-throughput`
**Release branch:** `main`
**Release MR/PR:** [#293](https://github.com/vadim-schultz/redtape/pull/293) — merged into `main` at `1ea2d76` (2026-11-01)

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `feat/discovery-throughput-budget-reallocation` | [#286](https://github.com/vadim-schultz/redtape/pull/286) | pass | pass | yes | none |
| 2 | `feat/discovery-throughput-same-day-pipeline` | [#287](https://github.com/vadim-schultz/redtape/pull/287) | pass (yaml parse + actionlint) | pass | yes | none (DISCOVERY_LLM_MODEL/schedule vars + extract/screenshot post-main smoke deferred to ch.6 per plan) |
| fix | `fix/discovery-throughput-workflow-test-sync` (ch.2 regression: 5 stale workflow-shape tests) | [#289](https://github.com/vadim-schultz/redtape/pull/289) | pass | pass | yes | none |
| 3 | `feat/discovery-throughput-optional-situation-codes` | [#288](https://github.com/vadim-schultz/redtape/pull/288) | pass | pass | yes | none (initial remote CI failure was the ch.2 regression above, resolved before merge) |
| fix | `fix/discovery-throughput-llm-enqueue-docs-sync` (ch.2 regression: LLM_ENQUEUE default-on drift in test_extraction_docs.py + discovery-online.md + extraction-operator-checklist.md + one scheduled-jobs.md line) | [#291](https://github.com/vadim-schultz/redtape/pull/291) | pass | pass | yes | none (OP13 checklist table/line-44/line-127 wording left for ch.5) |
| 4 | `feat/discovery-throughput-completeness-priority-claim` | [#290](https://github.com/vadim-schultz/redtape/pull/290) | pass | pass | yes | none (initial remote CI failure was the ch.2 LLM_ENQUEUE regression above, resolved before merge) |
| 5 | `feat/discovery-throughput-operator-docs-sync` | [#292](https://github.com/vadim-schultz/redtape/pull/292) | pass (stale-cron grep + apps/api suite) | pass | yes | none (2 minor non-blocking doc staleness spots in extraction-operator-checklist.md noted for future polish: "06:00 UTC" line ~233, LLM_ENQUEUE-rollback wording ~256-257 — not in required grep, no pinned test) |
| 6 | `feat/discovery-throughput-schedule-activation` (no branch/PR — pure `gh variable set`, per chapter) | n/a | n/a | n/a | yes (state change applied directly) | `gh variable list` confirms all 5 `DISCOVERY_*_SCHEDULE=enabled` + `DISCOVERY_LLM_MODEL=@cf/qwen/qwen3-30b-a3b-fp8`; Render-dashboard 2000/1000 override confirmed by user before running. `discovery-drain/render/llm.yml` live-verified (render re-dispatched successfully after setting LLM_MODEL, fixing the earlier D8 hard-fail). `discovery-extract.yml`/`discovery-screenshot.yml` not yet registered with GitHub — new files only exist on the loop branch; they'll register and become live once the release PR merges to `main`. Full day's same-day-completion verification deferred until after release. |

## Post-release verification

- Release PR [#293](https://github.com/vadim-schultz/redtape/pull/293) merged into `main` at `1ea2d76` (2026-11-01), fast-forward, all required checks (`lint-and-test` ×2, `migrations`, `Workers Builds: redtape-web`) passed.
- Confirmed via `gh workflow list --all`: `Discovery extract` (id 403434425) and `Discovery screenshot` (id 403434427) are now `active` on `main` — the ones that couldn't register pre-release. No runs yet (expected; they fire on their 04:00/05:00 UTC cron or `workflow_dispatch`).
- **Open follow-up, not yet done:** per the suite's exit criteria, confirm after one full day that a page fetched that morning reaches `capture_screenshot` the same day. This needs a same-day check once the schedules have actually fired post-release — revisit this ledger then.
- **Minor non-blocking doc polish carried forward** (noted by ch.5, not fixed): `docs/operations/extraction-operator-checklist.md` still says "The run is daily at 06:00 UTC" (~line 233, stale — real time is 04:30 UTC) and still frames rollback as "set `LLM_ENQUEUE` back to false" (~lines 256-257, stale — it's hardcoded `"true"` in the workflow YAML now, not an operator-settable variable). Candidate for a tiny future fix-forward.
