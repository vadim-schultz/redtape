---
name: Discovery operations — Gaps and decisions
overview: "Settled decisions for one-row verification, queue telemetry, bounded drains, and icon-based discovery navigation."
isProject: false
---

# Discovery operations — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **This suite operates the existing staging path.** The representative flow is GovData/PVOG catalogue ingest, durable task work, FIM enrichment, claims, T4 preview, and one manual emit. |
| D2 | **Staging is not canonical.** Emit creates `pending` suggestions; no operation in this suite approves, promotes, or silently writes canonical documents. |
| D3 | **Workers remain HTTP-only.** `apps/discovery-ingest` uses the machine API and API key; it never receives `DATABASE_URL` and never imports API persistence modules. |
| D4 | **Run success is explicit.** Do not infer the last successful drain from fetch timestamps. Persist a minimal `discovery_run` operational record, or an equivalent machine-API run event with the same lifecycle and report fields. The implementation chapter must choose the least invasive form before coding. |
| D5 | **Metrics are defined by database state.** Total, pending, claimed, completed, and failed are task counts; fetch attempts are `discovery_fetch_log` counts; stale claims are claimed tasks whose lease has expired; per-source failures join tasks to `catalogue_service.source`. |
| D6 | **Drain progress is bounded.** A run stops on an empty queue, a configured batch-count bound, or a configured wall-clock budget. A default one-batch invocation remains valid for safe smoke tests. No unbounded `while pending` loop is permitted. |
| D7 | **Existing queue guarantees remain.** Preserve the 1–50 claim limit, priority/created ordering, 15-minute lease, reclaim-on-claim behavior, failed-task reporting, catalogue upsert idempotency, fanout deduplication, and claim fingerprint deduplication. |
| D8 | **Remaining work is observable without leaking claims.** The worker must not claim one extra task merely to estimate backlog. Use the queue-summary contract from the observability chapter, or report remaining as unknown when that contract is unavailable. |
| D9 | **Discovery links become icon controls.** Catalogue uses `FaList`, Coverage uses `FaTasks`, and Tasks uses `FaClipboard` from the installed `react-icons/fa` family, subject to export verification during implementation. No new icon dependency is allowed. |
| D10 | **Accessibility is retained.** Icon-only controls have translated `aria-label` values and title or tooltip text, preserve keyboard focus and stable routes, and remain hidden unless the existing server admin probe succeeds. |
| D11 | **Crawler and evidence are deferred.** Do not create `apps/crawler`, extractors, Playwright capture, screenshots, evidence uploads, or the chapter-20 frontier adapter in this suite. Keep stable catalogue, task, entity, claim, and run identifiers usable by that future work. The crawl work is now planned as the queue-based [crawlers suite](../crawlers/00-architecture.md) (no standalone `apps/crawler` package). |
| D12 | **Manual emit remains deliberate.** Scheduled ingestion and worker drains do not emit automatically. The smoke chapter performs one explicit emit only after preview and T4 verification. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Dedicated run table versus append-only run event | Implementation needs to choose the smallest persistence change that can distinguish successful, failed, interrupted, and stale runs |
| Automatic retry policy for failed tasks | Operators need retries independent of the next catalogue refetch |
| Queue summary authentication surface | Worker needs remaining-count telemetry without granting admin JWT access |
| Coverage percentages against an authoritative source universe | Source ingest establishes a stable expected total rather than only imported-row counts |
| Icon-only discovery links versus a future labelled admin group | The admin menu grows beyond the three initial destinations |

## Deferred

- Full `apps/crawler` package and source-specific extraction.
- Robots-aware broad crawling and link-following frontier behavior.
- Playwright screenshots and evidence storage.
- Automatic emit, votes, moderation, and canonical promotion.
- LLM extraction and unresolved requirement discovery.
