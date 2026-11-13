---
name: Pipeline optimisation — Gaps and decisions
overview: "Settled decisions for the pipeline optimisation suite, the open seams that need a spike or an operator answer, and what is deferred."
isProject: false
---

# Pipeline optimisation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision | Source |
| --- | --- | --- |
| D1 | The Actions pool is the Free plan's 2,000 minutes a month. CI is the largest consumer, so the drain budget comes from measured use, not from the assumed 1,000 | operator |
| D2 | The LLM schedule returns after the verification query in operator step S2. The verification is the one in `.plans/category-taxonomy-remediation/run-ledger.md` (part C of `c8_queries_4.sql`) | operator and evidence |
| D3 | The long tail of card translation uses Azure for the top priority tier and Workers AI `llm` for the rest. Cards only: pages stay on Azure | operator, refined by review |
| D4 | Idle capacity is filled with change-driven refresh, a wider catalogue ingest and backfills | operator |
| D5 | One pipeline job runs its stages as subprocesses in three phases, not as followers. The old stage workflows stay dispatch-only, and `discovery-extract.yml` is deleted in chapter 15 | default |
| D6 | Change detection comes before any commitment to Browser Sessions. Sessions is a spike with a runner-local fallback | default |
| D7 | A rolling neuron ledger is built only if chapter 3 shows that the window is the cause of the 4006 refusals | default |
| D8 | No new infrastructure: no Worker-hosted drain and no external cron trigger. Both are deferred | default |
| D9 | This suite supersedes the stage timing and the claim-ordering clause of [discovery-throughput](../discovery-throughput/gaps-and-decisions.md) D5 where it touches the pipeline job, and updates the figures in [gha-budget](../../docs/operations/gha-budget.md) | default |
| D10 | Screenshot Tabs appear on the public candidate detail page only. The admin thumbnail row is unchanged | operator |
| D11 | Screenshots are kept as the latest five per page (`SCREENSHOT_KEEP_PER_PAGE`, default 5). That bounds the Tabs and the R2 growth | operator |
| D12 | The flow graph is a new admin page. Coverage stays. It uses a new shared `FlowGraph`, and the candidate `FlowDiagram` is not migrated | default |
| D13 | `CandidateDetail.screenshot` stays next to the new `screenshots[]` until the web and API deploys have both moved | default |
| D14 | A new translation tail is off by default. `TRANSLATION_TAIL_LOCALES` is empty until a locale passes the probe, so nothing reaches Workers AI by accident | default |
| D15 | A 429 from Azure releases the work without consuming an attempt. A failure that is not transient still consumes one | default |
| D16 | Flags for new behaviour (`RENDER_FUSED_SCREENSHOT`, `PIPELINE_ORCHESTRATOR`, `SEARCH_TAIL_TRANSLATION`) default to off. Each is turned on only after its live gate is recorded | default |

## Open seams

| Seam | Forcing condition | Owner |
| --- | --- | --- |
| The real Actions pool and CI usage | Operator reads the November usage report (operator step S1). The estimate of about 1,820 minutes in 13 days is per-run rounding, not billing data, and no job has failed, so the estimate may be high or the pool may differ | operator, chapter 1 |
| The cause of the 4006 neuron refusal on 2026-11-11 | Chapter 3 compares the ledger with Cloudflare's usage for each day | chapter 3 |
| Browser Sessions cost per page | Chapter 10 measures pages per billed minute; session time may accrue while idle | chapter 10 |
| Fused-call DOM parity | The canary in chapter 8 compares `/content` with the fused `/snapshot` on about 25 stable pages | chapter 8 |
| Workers AI quality for the card tail | No recorded `llm` probe numbers for the tail locales (tr, ru and uk were 60 to 70% valid on Azure). Chapter 7 gates each locale on a probe | chapter 7 |
| Azure F0 reset boundary | Calendar month or subscription anniversary (`azure-translation` O4). The pacing in chapter 6 assumes the ledger's UTC month, so the portal's answer is recorded in step S6 before chapter 6 merges | operator |
| Database size | The 475 MB soft limit stops machine writes. Measure before chapters 8 and 11 raise throughput | chapters 8, 11 |
| Render API load | Every discovery claim recomputes the completeness subquery, and concurrent stages multiply it. Watch the claim latency in the first phased runs | chapter 12 |
| R2 with screenshot history | Five captures at about 0.75 MB a page can reach about 5 GB of the 9.5 GB cap if every page were re-shot. Change detection should keep that rare, and the flow page shows the R2 meter | chapters 8, 11, 14 |
| Flow-graph state thresholds | The 1.5 times cadence, 2 times cadence and headroom share are first guesses. They sit in one table in the topology module and are tuned after a week of real data | chapter 13 |
| The graph's honesty | Until chapter 2 lands, only `worker drain` stages have a last run. Embedding and translation show as "no run recorded" rather than a stop reason | chapter 2 |
| Starvation traps | A per-stage neuron cap that sums above the ledger starves the last stage. A tail cap computed before extraction runs starves extraction. A second cron slot that is not idempotent double-spends the day. Refresh without pruning exhausts R2 | chapters 5, 12, 8 |

## Deferred

- A Worker-hosted drain and an external cron trigger (D8).
- A rolling neuron ledger (D7), unless chapter 3 says otherwise.
- Block-level translation memory. Chapter 6 measures the hit rate first and builds only if it justifies the table.
- Page translation on Workers AI.
- A Sessions implementation. It is a conditional follow-up only if chapter 10 says go and chapter 8 has landed.
- Migrating the candidate `FlowDiagram` onto `FlowGraph` (D12).
