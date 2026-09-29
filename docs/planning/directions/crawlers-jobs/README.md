# Strand: Crawlers and background jobs

## Scope

Two crawler **modes** (may share libraries, different configs and entrypoints):

1. **Freshness / reference maintenance** — crawl targets tied to **existing** documents and official URLs; update link health, metadata, optional scheduled **screenshot** capture for evidence refresh.
2. **Discovery** — initial or periodic broad crawl from seed URLs; propose new documents or requirements into a **review queue**; no silent merge into canonical graph without policy (votes/moderation).

Cross-cutting: **robots.txt** and rate limits, user-agent policy, fetch logging, deduplication, idempotent writes, object storage uploads for captures.

Discovery output is submitted through the shared suggestion API, not a bespoke ingestion path — see
[`.plans/suggestion-interface/`](../../../../.plans/suggestion-interface/00-architecture.md) for the shipped
data model and [`docs/operations/suggestion-api.md`](../../../operations/suggestion-api.md) for the request/response
contract, error codes and `Idempotency-Key` handling that [`crawlers` chapter
2](../../../../.plans/crawlers/chapters/02-suggestion-api-client.md) builds its API client against.

## Dependencies on other strands

- **data-model-migrations:** tables for targets, jobs, fetch logs, blob keys.
- **social-moderation:** how proposals are created from crawler output.
- **devops-ci-cd:** scheduling (GitHub Actions, worker process, queues).

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-job-runner-and-scheduling.md` | (TBD) Process model, cron, queues. |
| `02-freshness-crawler.md` | (TBD) Inputs, outputs, screenshot pipeline. |
| `03-discovery-crawler.md` | (TBD) Seeds, breadth limits, dedup, proposal creation. |
| `04-ethics-and-compliance.md` | (TBD) robots.txt, ToS, logging. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
