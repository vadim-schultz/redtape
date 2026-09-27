---
name: Crawlers — Gaps and decisions
overview: "Settled decisions and open seams for the crawler package, its fetching policy, and its GitHub Actions schedule."
isProject: false
---

# Crawlers — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Discovery only, not freshness.** This suite proposes new documents; it does not re-check existing ones. The strand's freshness mode is a separate future suite (open seam below), because it has a different shape (update, not create) that would otherwise pull the suggestion model toward an `edit_document` kind before that is needed. |
| D2 | **A separate package (`apps/crawler`), not a script inside `apps/api`.** Playwright's browser binary is large and irrelevant to the API's deploy image; and the crawler must never import the database session (D3 below), which is easiest to guarantee by giving it no access to `app.db` at all. |
| D3 | **No database access, ever.** The crawler only calls the public HTTP API with an API key, the same interface a third-party integrator would use. This is a deliberate constraint, not a shortcut: it is what makes the suggestion API a real product surface instead of an internal implementation detail, and it means a crawler bug can never corrupt the database directly. |
| D4 | **GitHub Actions, not a worker process** (program decision D3, Render's free tier has no background worker). A run is bounded by the workflow's `timeout-minutes`, same discipline as `openplz-import.yml`. |
| D5 | **One extractor per source shape**, dispatched through a registry, not a single generic HTML scraper. A generic scraper for arbitrary government sites would be unreliable; a small number of hand-written extractors for known portals is honest about the effort involved. |
| D6 | **Idempotency via a stable hash of the source URL**, sent as the API's `Idempotency-Key`. Re-running a scheduled job (retry after a transient failure, or a manual re-dispatch) never creates duplicate suggestions. |
| D7 | **A 409 from the suggestion API is a normal, logged outcome, not a run failure.** The run report counts duplicates separately from errors so operators are not paged for expected behaviour. |
| D8 | **Playwright over a simpler screenshot method** (e.g. a third-party screenshot API) to avoid a second external dependency and keep evidence capture inside the crawler's own process, at the cost of the heavier CI job. |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Freshness crawling (link health, metadata refresh on existing documents) | Not built | Product decides stale documents are a visible problem |
| More than one extractor | One real source (S1 in the program plan) | Each new source needs its own extractor chapter, same shape as chapter 6 |
| JavaScript-heavy sources needing interaction (pagination clicks, login walls) | Playwright loads the page but nothing more | First source that needs it |
| Crawl budget / breadth limits for a true discovery crawl (following links, not just configured seeds) | Sources are a fixed, manually maintained list; no link-following | Someone wants the crawler to find sources itself, not just process a curated list |
| Alerting on repeated extractor failures | The run report is the only signal (read manually or via workflow failure) | First silent extractor breakage goes unnoticed for a while |
| Rate-limit and robots.txt policy shared with a future freshness crawler | Duplicated into `apps/crawler` today (`PoliteFetcher`) rather than shared with `apps/api`'s `openplz_client.py` | If a third HTTP client appears, extract a shared library then, not before (rule of three) |
