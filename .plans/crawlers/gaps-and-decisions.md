---
name: Crawlers — Gaps and decisions
overview: "Settled decisions, open seams, and recorded risks for the queue-based document-first crawl layer."
isProject: false
---

# Crawlers — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Queue consumer.** The crawl layer consumes the existing `discovery_task` queue. There is no standalone `apps/crawler` package, no `sources.yaml`, and no direct `POST /suggestions` from workers. |
| D2 | **New task kinds in the same table.** `harvest_payload`, `extract_page` and `capture_screenshot` extend the existing enum, and `render_page` joins them in chapter 14. Separate tables or queues were rejected: they would rebuild leases, reclaim, dedup, metrics and the admin Tasks view. |
| D3 | **Kind-filtered claim, safe default.** Workers send `kinds`; when omitted the API serves only the two legacy kinds so the scheduled drain cannot lease and fail an unknown kind. |
| D4 | **Workers orchestrate, API persists.** Follow-up tasks are enqueued by the worker through an idempotent machine route because only the worker knows which extractors exist. Workers never hold `DATABASE_URL`. |
| D5 | **A procedure is not a document.** Catalogue services stay staging context. Document nodes come only from what a procedure requires or provides (forms, evidence, documents to bring). Service-level `new_document` claims from FIM enrichment stay staged and are excluded from the document-first path. |
| D6 | **Documents first, edges later.** This suite harvests, deduplicates, reviews and emits document candidates. Mentions keep the `requires` relation so the later dependency-graph suite needs no re-crawl. |
| D7 | **Candidate key equals the promotion slug rule.** `key = slugify(pick_title(title_i18n))` from [slugs.py](../../apps/api/app/features/suggestions/slugs.py), so two candidates never collide at promotion that did not already collide as candidates. |
| D8 | **`official_url` becomes optional on `new_document`.** Conflicts are detected on slug or normalized URL per jurisdiction ([handlers.py](../../apps/api/app/features/suggestions/handlers.py)), so a shared procedure URL cannot serve as a fallback. Many documents ("Personalausweis") have no URL of their own. The change is additive; `Document.official_url` is already nullable; provenance travels in `suggestion.source_url`. |
| D9 | **Both artifact kinds live in the object store; Postgres holds metadata only.** Rejected alternative: gzip'd `bytea` snapshots in Postgres (about 12–20 MB for today's 1,423 pages). The free database is capped at 500 MB and goes read-only on overflow, whereas a full bucket only blocks uploads. |
| D10 | **Supabase Storage first, behind an `ObjectStore` port.** One S3 adapter; R2 is a configuration swap. The earlier evidence-storage plan chose R2 before anything was built; that suite is amended in chapter 21. |
| D11 | **Uploads are proxied through the API.** Storage credentials live only in Render. Reads use five-minute presigned GET URLs minted per request. |
| D12 | **Snapshots are working input, screenshots are evidence.** Snapshots: the rendered DOM as `text/html`, 4 MB cap (a rendered DOM is larger than the raw response), latest two per service, deduplicated by sha256. Screenshots: PNG or JPEG, 8 MB cap, durable. HTML is never rendered inline in the admin. |
| D13 | **Screenshots only for pages that yielded documents.** A screenshot task is enqueued only after an extraction produced at least one mention, and login walls are skipped. Evidence of a login page has no value. The Cloudflare snapshot endpoint could return an image for every page at no extra call, but 1,423 images would approach the 1 GB storage cap and spend browser time on pages that yield nothing. |
| D14 | **Pages are rendered by Cloudflare Browser Run quick actions, not by a browser we run.** The worker calls `/content` (rendered DOM) and `/snapshot` (DOM plus image) through a `BrowserClient` port with a Cloudflare adapter. No Playwright, no `[capture]` extra, no Chromium install, no browser CI job, no browser in any image. This replaces the earlier decision to run Playwright in a dedicated workflow; the rendered DOM also makes JavaScript shells (such as `fimportal.de/detail/...`) extractable. The Cloudflare account already hosts the frontend, so the free plan costs nothing. |
| D15 | **Retries only for transient failures.** 5xx, timeout and connection reset re-pend with backoff up to a cap; 4xx stays failed. |
| D16 | **Manual emit remains deliberate.** Scheduled jobs never emit. Candidate emit is idempotent per candidate and records the suggestion on the candidate. |
| D17 | **GitHub Actions is the test bench.** Local development is limited, so chapters verify with PR checks and `gh workflow run`; the non-production stack may be used freely. |
| D18 | **Navigation links are `react-icons` buttons in one `HStack` row,** driven by the config array. Never a new row, never a text link. |
| D19 | **The plain fetch stays the gate; Cloudflare renders.** `fetch_url` keeps its robots, pacing, redirect and status handling and logs the outcome. Only a 200 `text/html` result whose final URL is not a login URL enqueues a `render_page` task. Browser time is never spent on redirects, errors or login pages, and the merged chapter 2 work stays useful. Rejected: replacing the plain fetch with a render (loses the status and redirect log, spends browser time on everything). |
| D20 | **The free-plan limits are a design input.** 10 browser minutes a day, one quick-action request every 10 seconds, 3 concurrent browsers, 60 s timeout. The worker serialises calls at least 11 s apart, sums `X-Browser-Ms-Used` against a per-run budget (default 480 s), and stops on `429`. The rate limit normally binds before the browser minutes (about 80 pages per 15-minute run). Browser kinds live in their own kind-filtered workflow and are never in the default kinds, so the HTTP drain never waits on the throttle. |
| D21 | **Limits release tasks; only pages fail them.** A quota `429`, an exhausted browser budget, or unavailable storage says nothing about the page, and attempts are consumed at claim time (cap 3). The worker therefore calls a new release route (`POST /machine/tasks/{id}/release`, chapter 14) for the in-flight task and every unstarted task of the batch, which re-pends them and gives the attempt back, then ends the run successfully. Browser drains claim small batches (5). |
| D22 | **The Cloudflare token is narrow and stays out of the API.** A custom token with only "Browser Run - Edit", stored as GitHub Actions secrets and in the operator's local environment. Quick-action requests are signed by Cloudflare (Web Bot Auth) and cannot hide that they are automated; the worker still checks robots.txt itself and sends its identifying User-Agent as the quick action's `userAgent`. |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Resolve mentions to canonical documents and emit `new_requirement` suggestions | Mentions are staged with roles; no emit | Enough documents promoted to reference |
| Web voting and moderation UI | API votes and promotion exist; the web screens are [voting-moderation](../voting-moderation/01-rollout.md) chapters 10–11 | Operators need to approve candidates without API calls |
| Attach artifacts to suggestions as `evidence` rows | Artifacts stay linked to staging only | [evidence-storage](../evidence-storage/00-architecture.md) model and routes ship |
| Re-extraction on extractor version bump | `input_key` makes it possible; no admin trigger | First extractor revision |
| Link-following frontier and crawl budgets | Not built; sources are catalogue `portal_url`s | Someone wants discovery of unseen pages |
| Freshness crawling | Not built | Product treats stale documents as a visible problem |
| LLM extraction | Deferred ([discovery-layer chapter 21](../discovery-layer/chapters/README.md)) | Hand-written extractors stop scaling across 123 hosts |
| Snapshot and screenshot retention beyond "latest two" | None for screenshots | Storage nears the 1 GB cap |
| Plain-first rendering: keep the plain body as the snapshot for pages that are already server-rendered and call Cloudflare only for thin shells | Every successful HTML page is rendered, so one snapshot shape feeds every extractor | The free allowance makes the render backlog too slow, or the probe shows most pages are static |
| Viewport-only screenshot retry for pages whose full-page JPEG exceeds 8 MB | Such pages complete with `oversize` and no image | Oversize notes appear on pages that matter |
| Paid Cloudflare plan | Not needed; lower `BROWSER_MIN_INTERVAL_SECONDS` to use it | The free throttle becomes the bottleneck for freshness work |
| Cloudflare R2 instead of Supabase Storage for artifacts | Supabase first (D10); the account already exists for the frontend | Storage nears the 1 GB cap |
| Rename `apps/discovery-ingest` | Keep the name | The package no longer fits its name |

## Risks

| Risk | Mitigation |
| --- | --- |
| Postgres enum labels cannot be removed on downgrade | Add all three labels in one migration; document the downgrade as label-preserving; rely on the kind filter for safety |
| boto3 default checksum headers may be rejected by Supabase's S3 layer | Live probe workflow decides the client checksum configuration before any upload code depends on it |
| 1 GB free Storage, 5 GB egress | Storage-bytes metric in Coverage; screenshots only for pages with mentions; rendered snapshots limited to the latest two per service at 4 MB; R2 swap documented |
| `fimportal.de/detail/L/...` pages may be JavaScript-rendered | Rendered by Cloudflare (D14), so the snapshot holds the DOM; chapter 15's probe compares a shell page's plain and rendered sizes. FIM API enrichment (chapter 12) and payload harvest remain the primary sources |
| The free Cloudflare allowance makes the render backlog slow | About 5 pages a minute and roughly 18 fifteen-minute runs for the known 1,423 pages; local runs cost no Actions minutes; pages are rendered in queue order, so partial progress is useful; plain-first (open seam) and the paid plan are the escape hatches |
| The quick action does not document its error or quota behaviour in detail | Chapter 15 starts with a probe that records response shape, `X-Browser-Ms-Used`, error cases and a `429` body; every limit is handled by release, so a surprise stops a run instead of failing tasks |
| Sites or WAFs may block Cloudflare's signed, automated traffic | Render failures are per page and retried with backoff; no bypass is attempted (invariant 8); the plain fetch result and PVOG payload harvest still exist |
| The Cloudflare token is a new credential in GitHub Actions | Scoped to Browser Run - Edit only, never in Render or the web app (invariant 11); rotate by replacing the secrets and running the probe |
| Page content is sent to a third-party browser service | Only public catalogue URLs are rendered; login walls are skipped |
| robots.txt and terms across 123 hosts | Respect robots.txt, identify the bot, rate limit per host, no login-wall bypass, skip on denial |
| Candidate names harvested from free text are noisy | Staged, deduplicated and reviewed before any emit; excerpts and source fields shown to the reviewer |
| The `.plans/README.md` status lines for voting-moderation lag the code | Noted in chapter 21; correcting another suite's status is left to its owner |
