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
| D3 | **Workers use HTTP only** — no `DATABASE_URL` on ingest/crawler ([crawlers D4](../crawlers/gaps-and-decisions.md)). |
| D4 | **No standing GHA discovery job.** |
| D5 | **Auto-enqueue** `discovery_task` on catalogue upsert. |
| D6 | **Admin pipeline read-only** — no approve/reject/hold in v1. |
| D7 | **Leistung → staging `catalogue_service`**; public graph uses **documents**. |
| D8 | **`new_requirement` needs UUIDs** — stub claims until entities resolve. |
| D9 | **COS skills** in `.cursor/skills/redtape-*` (chapters 08–11). |
| D10 | **Loop-complete boundary.** CoS ships staging, machine + admin APIs, `/admin/discovery/*`, four gov skills, `apps/discovery-ingest` CLIs, fan-out/dedup/coverage, machine emit to suggestions (pending only), runbook + docs. No crawler package, no voting, no evidence attachments in-loop. |
| D11 | **Deferred chapters.** 16 (claim evidence) → after evidence-storage; 20 (crawler frontier) → crawlers suite; 21 (LLM extract) → open seam. Not in [01-rollout.md](01-rollout.md) execution order. |
| D12 | **`apps/discovery-ingest/`** is a separate package (like `apps/crawler/`): httpx clients, fixtures, thin CLIs; **no** `DATABASE_URL` or `app.db` imports; all writes via discovery machine API + API key. |
| D13 | **PVOG API default host** `pvog.fitko.net` (`PVOG_API_BASE_URL` override). Product portal may remain `pvog.fitko.de`. |
| D14 | **LeiKa enrich** uses FIM Portal REST + [Kataloge](https://fimportal.de/kataloge) bulk exports — not a separate API host. Canon: [docs/discovery/government-data-sources.md](../../docs/discovery/government-data-sources.md). |
| D15 | **Corporate proxy** for manual GovData/PVOG/FIM access: [corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md). CI ingest tests use fixtures only — no standing egress to government APIs. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| T4 search | Documents not found by links |
| CF cron drain endpoint | Scheduled runs without laptop |
| `role=admin` instead of email allowlist | Second operator |
