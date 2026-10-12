---
name: Discovery layer — Gaps and decisions
overview: "Settled decisions and open seams for staging ingest, admin pipeline review, and crawler coordination."
isProject: false
---

# Discovery layer — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Public UX is documents-only.** Pipeline stages appear only under `/admin/discovery/*`. |
| D2 | **Staging ≠ canonical.** Promotion only via [voting-moderation](../voting-moderation/00-architecture.md). |
| D3 | **Workers use HTTP only** — no `DATABASE_URL` on ingest/crawler ([crawlers D3](../crawlers/gaps-and-decisions.md)). |
| D4 | **No standing GHA discovery job.** |
| D5 | **Auto-enqueue** `discovery_task` on catalogue upsert. |
| D6 | **Admin pipeline read-only** — no approve/reject/hold in v1. |
| D7 | **Leistung → staging `catalogue_service`**; public graph uses **documents**. |
| D8 | **`new_requirement` needs UUIDs** — stub claims until entities resolve. |
| D9 | **COS skills** in `.cursor/skills/redtape-*` (chapters 08–11). |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| T4 search | Documents not found by links |
| CF cron drain endpoint | Scheduled runs without laptop |
| `role=admin` instead of email allowlist | Second operator |
