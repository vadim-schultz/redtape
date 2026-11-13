# Pipeline optimisation chapters

The chief-of-staff execution order is defined in [../01-rollout.md](../01-rollout.md).

| # | Chapter | Purpose |
| --- | --- | --- |
| 1 | [CI minute diet and real-minute reconciliation](01-ci-minute-diet.md) | Cut CI minutes and measure what CI really bills, so the drain budget is sized from data |
| 2 | [Observability and run hygiene](02-observability-run-hygiene.md) | Settle failed browser calls once, record a run for every drain, close stale runs, and expose the queue stats the flow needs |
| 3 | [Neuron reconciliation spike](03-neuron-reconciliation-spike.md) | Decide whether the 4006 refusals come from a rolling window, unledgered spend or estimate error |
| 4 | [Queue hardening](04-queue-hardening.md) | Dedup by artifact, lock the discovery claim, persist failure classes and requeue transient failures |
| 5 | [LLM readiness](05-llm-readiness.md) | Make neuron spend thread-safe, run the LLM stage concurrently, and requeue the prompt-stale extractions |
| 6 | [Azure economy](06-azure-economy.md) | Treat 429 as a release, pace the characters per minute and per day, and measure translation-memory hits |
| 7 | [Tiered translation routing](07-tiered-translation-routing.md) | Route the card tail to Workers AI by priority, and let Azure supersede it later |
| 8 | [Fused render, screenshot sweeper and pruning](08-fused-render-screenshot-sweeper.md) | One browser call per page for HTML and screenshot, a screenshot sweeper, and pruning to five captures |
| 9 | [Screenshot history Tabs](09-screenshot-history-tabs.md) | Show up to five captures on the candidate page as Tabs, newest first and active |
| 10 | [Browser Sessions spike](10-browser-sessions-spike.md) | Measure Browser Sessions over CDP against the runner-local fallback, and record a go or no-go |
| 11 | [Funnel: change detection, refresh and ingest split](11-funnel-change-detection.md) | Re-render only changed pages, refresh on an epoch, and split the catalogue ingest from OpenPLZ |
| 12 | [Pipeline orchestrator and single workflow](12-pipeline-orchestrator.md) | Run the stages in three phases from one job, with one deadline and one report |
| 13 | [Pipeline flow API](13-pipeline-flow-api.md) | Topology, the stage state rules and the flow route with spend per stage |
| 14 | [Admin pipeline flow graph](14-admin-pipeline-flow-graph.md) | The shared `FlowGraph` and the admin flow page |
| 15 | [Docs, drift fixes and staged activation](15-docs-activation.md) | Operator docs, the drift list, deletion of the retired workflow, and the activation walkthrough |

Each chapter has: Goal, Design (concrete file paths and decisions), Red tests (paired happy and negative), Green, Refactor gate, Verification, Commits, Out of scope and Git workflow. Chapters 1, 3, 6 and 10 are in wave 0 and can run in parallel.
