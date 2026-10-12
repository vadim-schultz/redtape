---
name: Discovery layer — Architecture
overview: "Tiered catalogue ingest into Postgres staging via Litestar machine APIs; auto-enqueued crawler tasks; read-only admin pipeline review; emit to suggestion API. Workers never hold DATABASE_URL."
isProject: false
---

# Discovery layer — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

The public product is **documents** and **dependencies** ([00-master-summary.md](../../docs/planning/00-master-summary.md)). This suite populates staging from GovData/PVOG/FIM/LeiKa and coordinates [crawlers](../crawlers/00-architecture.md); [suggestion-interface](../suggestion-interface/00-architecture.md) remains the moderation boundary.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Staging graph** | `catalogue_service`, `discovery_entity`, `discovery_claim`, `discovery_task`, `discovery_fetch_log`, `discovery_event` |
| **Pipeline stage (T0–T4)** | Admin-only ingest/fetch/extract labels |
| **Auto-enqueue** | Catalogue upsert creates `discovery_task` immediately |
| **Admin pipeline review** | Read-only ops UI — no approve/reject |

## 3. Architecture

```mermaid
flowchart TB
  ingest[GovData_PVOG_FIM] --> CLI[ingest_CLI]
  CLI --> DiscAPI[discovery_API]
  DiscAPI --> staging[(Postgres_staging)]
  DT[discovery_task] --> Crawler[crawler_CLI]
  Crawler --> DiscAPI
  DiscAPI --> Sug[suggestion_API]
  Sug --> Cat[document_graph]
```

## 4. Admin UI

`/admin/discovery/*` — crawler queue, catalogue index, pipeline drill-down, emit preview. Email allowlist (`DISCOVERY_ADMIN_EMAILS`). Not in public navigation.

## 5. Write boundaries

| Client | DATABASE_URL |
| --- | --- |
| Litestar | yes (staging only) |
| Ingest/crawler CLIs | **no** — API key |
| OpenPLZ GHA | yes — locations only |

## 6. Admin pipeline review (read-only)

Auto-enqueue crawlers; **no** approve/reject in admin. Screens:

| Screen | Route | Purpose |
| --- | --- | --- |
| Crawler targets | `/admin/discovery/tasks` | What crawlers will claim next |
| Catalogue index | `/admin/discovery/catalogue` | Imported rows + summary chips |
| Pipeline drill-down | `/admin/discovery/pipeline/:id` | T0 → T1 → fetches → claims → emit per row |
| Emit preview | section on drill-down | `GET …/emit-preview` — no POST to suggestions |

Admin API paths: [01-rollout.md](01-rollout.md). Public app remains documents-only.

## 7. Prerequisites

[voting-moderation](../voting-moderation/01-rollout.md), [evidence-storage](../evidence-storage/01-rollout.md) (screenshots), [crawlers](../crawlers/01-rollout.md) ch.1–5 (adapter).
