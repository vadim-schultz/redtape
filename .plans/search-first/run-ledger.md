# Search-first — Run ledger

**Suite:** [00-architecture.md](00-architecture.md) · [01-rollout.md](01-rollout.md)
**Purpose:** Record implementation and post-deploy evidence. This file is a ledger template; no production checks are implied by its creation.

## Orchestration

- Loop branch: `feat/plans-search-first`
- Release branch: `main`
- Local CI: `./ci.sh`
- Implementation and integration order: `C1 → C2 → C3 → C7 → C4 → C13 → C5 → C6 → C14 → C8 → C15 → C16 → C12 → C9 → C10 → C17 → C11 → C18`
- Parallel batches: `B1=C1,C2`, `B2=C3,C7`, `B3=C4,C13`, `B4=C5`, `B5=C6,C14`, `B6=C8,C15,C16`, `B7=C12`, `B8=C9`, `B9=C10`, `B10=C17`, `B11=C11`, `B12=C18`
- Environment: web installs use `npm ci` against the corporate npm mirror; `./ci.sh` runs `uv run`, which may rewrite `apps/discovery-ingest/uv.lock` to the corporate PyPI mirror. Revert that file before committing (except the intentional C1 dependency change in `apps/api`).
- Status: planned; no chapter started.
- Conflicts/failures: none.
- Current work: none.

## Merge ledger (chief of staff)

**Loop branch:** `feat/plans-search-first`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_
**Execution order:** the rollout's "Integration order" (C1 → C2 → C3 → C7 → C4 → C13 → C5 → C6 → C14 → C8 → C15 → C16 → C12 → C9 → C10 → C17 → C11 → C18). C18 is `chief-of-staff` execution (operator actions, live validation) and is not run by an implementer.

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file; chapter evidence above is filled by the chief of staff from implementer returns.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 01-infra-and-embedding-probe | `feat/search-infra-and-probe` | [#372](https://github.com/vadim-schultz/redtape/pull/372) (+ [#373](https://github.com/vadim-schultz/redtape/pull/373) typer pin) | pass | pass | yes (64ef112) | none |
| 02-backend-locale-foundation | `feat/search-backend-locales` | [#374](https://github.com/vadim-schultz/redtape/pull/374) | pass | pass | yes (5ccabc4) | none |
| 03-search-schema | `feat/search-schema` | [#375](https://github.com/vadim-schultz/redtape/pull/375) | pass | pass | yes (edfffd9) | none |
| 07-web-locale-foundation | `feat/web-locale-foundation` | [#376](https://github.com/vadim-schultz/redtape/pull/376) | pass | pass | yes (5ca91a0) | none |
| 04-search-text-builder-and-backfill | `feat/search-text-builder` | [#377](https://github.com/vadim-schultz/redtape/pull/377) | pass | pass | yes (5886ba5) | none |
| 13-translation-schema-and-core | `feat/translation-schema-and-core` | [#378](https://github.com/vadim-schultz/redtape/pull/378) | pass | pass | yes (76ff271) | native-speaker spot checks pending (manual) |
| 05-embedding-task-machine-api | `feat/embedding-task-api` | [#380](https://github.com/vadim-schultz/redtape/pull/380) | pass | pass | yes (6d58b2c) | none |
| 06-embedding-drain-worker | `feat/embedding-drain-worker` | [#382](https://github.com/vadim-schultz/redtape/pull/382) | pass | pass | yes (cc27440) | operator steps pending (secrets, backfill, first dispatch) |
| 14-translation-queue-and-machine-api | `feat/translation-task-api` | [#384](https://github.com/vadim-schultz/redtape/pull/384) | pass (`ci.sh` copy with scratch DB names `redtape_c14_*`) | pass | yes (e262174) | operator steps pending (narrow target locales, backfill, R2 vars) |
| 08-hybrid-query-path | `feat/hybrid-search` | [#386](https://github.com/vadim-schultz/redtape/pull/386) | pass (`ci.sh` copy with scratch DB names `redtape_c8_*`) | pass | yes (21a86d4) | operator steps pending (Render token, flag, XFF check) |
| 15-translation-drain-worker | `feat/translation-drain-worker` | [#388](https://github.com/vadim-schultz/redtape/pull/388) | pass (`ci.sh` copy with scratch DB names `redtape_c15_*`) | pass | yes (dc32628) | operator steps pending (backfill, narrow locales, R2 vars, secrets, schedule variable, first dispatch) |
| 16-translated-text-in-search-and-embeddings | `feat/translated-search-text` | [#390](https://github.com/vadim-schultz/redtape/pull/390) | pass (`ci.sh` copy with scratch DB names `redtape_c16_*`; web build and later stages run by hand after the copy hit its timeout) | pass | yes (a1a4e95) | operator steps pending (per-locale search backfill, embed drain, optional `EMBEDDING_LOCALES`) |
| 12-combined-ranking-score | `feat/combined-ranking` | [#392](https://github.com/vadim-schultz/redtape/pull/392) | pass (`ci.sh` copy with scratch DB names `redtape_c12_*`) | pass | yes (2fa14cd) | none |

## Baseline

| Check | Expected evidence | Recorded |
| --- | --- | --- |
| Candidate count and text sizes | Row count of `discovery_document_candidate`; p50/p95 canonical text and translation-unit length | pending |
| Current search behaviour | `q` title-match results for a fixed set of German queries, kept as the keyword baseline | pending |
| No-sort ordering | What `GET /api/v1/candidates` returns with no `sort_by` (open seam O6) | pending |
| Database size | `pg_database_size` against `DB_SOFT_LIMIT_BYTES` (product owner's figure: about 83 MB of 500 MB; record the measured value) | pending |
| Object storage | Bucket bytes and objects today (screenshots, snapshots), R2 Class A and B usage this month against the caps | pending |
| Neuron ledger | Daily neuron budget and current usage | pending |
| UI baseline | Screenshots of `/documents` (de) at desktop and mobile width | pending |
| Locale bundles | Key counts per locale file and per prefix | pending |

## Chapter evidence

### Chapter 1 — Infra and embedding probe

- Status: merged into loop branch (#372); refactor gate: Long Function in `CloudflareEmbeddingClient.embed` -> Extract Function; data-design gate: not applicable
- pgvector version (local image, CI image, Supabase): local/CI `pgvector/pgvector:pg16`, vector 0.8.7 on PG 16.15; Supabase not checked (operator action)
- Probe (2026-11-10, `embed probe` from PR #372, live Workers AI): model `@cf/qwen/qwen3-embedding-0.6b`, dimension 1024; reduced dimensions 768/512/256/128 NOT honoured (`dimensions` returned 1024); batches 1–256 all accepted (no rejection up to 256); single-text latency 359 ms (batch 256: 3.6 s); 7,931 tokens, 8.52 neurons, 1.07 neurons per 1k tokens. Request/response shape assumed by the client confirmed.
- pgvector on Supabase (operator, 2026-11-10): `vector` 0.8.0 available, not yet installed (C3 migration runs `CREATE EXTENSION`); `unaccent` 1.1 available, not installed.
- Measured baseline: `pg_database_size` 58,707,091 bytes (about 58.7 MB, not the 83 MB estimate); 4,713 candidates.
- Gate decision: `EMBEDDING_DIM=1024`, column type `halfvec(1024)` (pgvector 0.8 supports halfvec and iterative HNSW scans); no reduced dimension (the model ignores `dimensions`). Projection for 4,713 x 7 = 32,991 rows: halfvec(1024) table+HNSW about 175 MB, plus search text/tsvectors about 41 MB (estimate, C3 measures), plus 58.7 MB baseline = about 275 MB versus `DB_SOFT_LIMIT_BYTES` 475 MB (about 200 MB margin). `vector(1024)` would be about 440 MB total (thin margin), so it is not chosen.

### Chapter 2 — Backend locale foundation

- Status: merged into loop branch (#374); refactor gate: smells found -> refactorings applied (`pick_i18n` loops extracted, seed split); data-design gate: reviewed, no `apply` findings (observed: stored `completeness_pct` now dead; accepted-risk: uncached `/locales` count)
- Locale rows seeded (enabled flags): 7 rows; de, en enabled; tr, ru, uk, pl, ro disabled. `ui_translation`: de 367 keys, en 367 keys; computed completeness de/en 100.0, others 0.0
- Resolution and validation tests: added (fallback chain, seed idempotence preserving `enabled`, locale-key validation rejects `fr`); non-German readers now fall back `en` before `de`

### Chapter 3 — Search schema

- Status: merged into loop branch (#375); refactor gate: smells found -> refactorings applied (`_candidate_id()` extracted in migration; test helper); data-design gate: no `apply` findings (accepted-risk: no index on `embedding_task.candidate_id`, redundant `dim`; observed for C4/C5: use matching `index_where` on enqueue upsert, retry cap/backoff and claim fencing)
- Migration id and round-trip result: `20261110_search_schema` (parent `20261105_retire_legacy_taxonomy`); `scripts/check_migrations.sh` passes (single head, upgrade, downgrade -1, upgrade, `alembic check`). Migration creates `vector` and `unaccent` extensions; on Supabase both are available but not installed, so the deploy role needs permission to create extensions, or an operator enables them first.
- `alembic check` with `Vector` and HNSW: passes with no hook; detects `halfvec(512)` vs `halfvec(1024)` drift and a dropped GIN index
- Table and index sizes (scratch DB, synthetic rows, `halfvec(1024)`, HNSW m=16 ef_construction=64): de only, 4,713 rows: embedding 27.4 MB (HNSW 12 MB), search text 26.2 MB (each GIN 5.1 MB), tasks 1.2 MB. Seven locales, 32,991 rows: embedding 191 MB (HNSW 86 MB), search text 133 MB (synthetic 60-word text, pessimistic), tasks 8.1 MB. Worst case 58.7 + 332 = about 391 MB vs 475 MB soft limit (about 84 MB margin); the C1 estimate of about 275 MB assumed shorter text. Re-check with real text lengths (C4 backfill, C16, C18). Levers: `EMBEDDING_LOCALES`, prune tool. HNSW `REINDEX` not measured.

### Chapter 4 — Search-text builder, hooks and backfill

- Status: merged into loop branch (#377); refactor gate: smells found -> refactorings applied (`upsert_search_text` helpers, `_upsert_pending` split, `BackfillReport` middle man removed, `RefreshTotals` Counter); data-design gate: 1 `apply` (A->B->A stale pending task retired, with happy and negative tests); accepted-risk: concurrent mention writers can lose an excerpt until next write/backfill, hot-candidate fan-out; observed: no reconcile for failed tasks or `EMBEDDING_MODEL` change (C5/C6/C18), retry cap and claim fencing (C5; skip re-queue when embedding already at current hash), `RECIPE_VERSION` bump needs a backfill (C18 runbook)
- Backfill counts (local scratch corpus only: synthetic 4,000 candidates / 17,849 mentions; NOT real data): run 1 processed 4000, written 3999, skipped empty 1, enqueued 3999; run 2 written 0, unchanged 3999, enqueued 0. `de` text length p50 1,117 / p95 1,499 chars (cap 1,500; synthetic, upper bound). Sizes: search text table 9.2 MB + two GIN 8.2 MB = 17 MB, tasks 1.3 MB. Real-corpus numbers come from the first real backfill (script prints the same line).
- Recipe version and hash stability check: `RECIPE_VERSION = "v1"`, `content_hash = sha256("v1\n" + text)`; deterministic with mention-order ties, idempotent re-run (0 rewrites via `xmin`, 0 task changes), a version bump changes every hash
- Interpretation: mention ordering uses `direct_category_confidence` desc (mentions have no score column); changing it needs a `RECIPE_VERSION` bump

### Chapter 5 — Embedding task machine API

- Status: merged into loop branch (#380); refactor gate: smells found -> refactorings applied (`search/clock.py` extracted, `FailureKind` replaces flag argument, `VECTOR_CHECKS` table, `reclaim_expired` split, `ready_clause`, `release` built once); data-design gate: 2 `apply` (complete holds `FOR SHARE` on the search-text row so a concurrent rewrite cannot be lost; locked `owned()` check makes settle atomic with reclaim; each with happy and negative tests); accepted-risk: zombie worker with same API key can settle a reclaimed claim (no lease token), replayed `complete` answers `rejected` (C6 must treat as non-fatal), `summary.stale_candidates` full join (revisit above 200k rows); observed: no retry jitter or age alert
- Contract fixture regenerated: `discovery_machine_contract.json` (+5 routes, 12 models) and the web `openapi.schemas.json`; contract tests pass
- Claim concurrency test (two claimers, no overlap): `test_two_concurrent_claimers_never_receive_the_same_task` (disjoint ids, union = all six; `lock_timeout` makes a missing `SKIP LOCKED` fail)
- Generic leased queue extraction; existing discovery queue tests unchanged: `features/search/leased_queue.py` (`LeasedQueue`, reusable by C14); lease and retry policy shared via `discovery/task_lease.py` and `task_retry.py`; `test_discovery_task_queue.py` unedited and green. SQL clauses stay per table (different native status enums)
- Deviations: `fail`/`release` answer 409 for unknown and foreign tasks; `release` takes optional `reason`; `complete` also marks stale when the hash differs from the leased hash; `summary` takes optional `model`; no recorded red run (tests written first, first run was green)

### Chapter 6 — Embedding drain worker

- Status: merged into loop branch (#382); refactor gate: smells found -> refactorings applied (`remaining_of`, `drain_loop.py`/`report.py` extracted, `_fail_tasks`, `_close_tally`, `Embedder` Protocol moved to `client.py`, embedding price single-sourced in `prices.py`); data-design gate: 1 `apply` (transport failure on claim/complete/fail crashed the drain and left the batch leased; `refusals_as_stops()` turns it into a stop, releases the batch, still prints the report; 3 negative tests); accepted-risk: one poison text fails a whole 50-batch on a provider 4xx (trigger: any `failed` from a 4xx), ledger over-charged by the conservative estimate after a crash between reserve and settle, worker/API `EMBEDDING_MODEL` mismatch looks like `queue_empty` (trigger: Render `EMBEDDING_MODEL` ever set); observed: no retry jitter or queue-age alert
- First drain report (claimed, completed, stale, neurons): PENDING (operator; no live call made)
- Cadence chosen and Actions minutes per run: `10 6,18 * * *` (every 12 hours, deviation from the 6-hour default, rationale in `docs/operations/gha-budget.md`), gated by `DISCOVERY_EMBED_SCHEDULE`. Estimates, not measured: idle run about 1.5-2 min (3 ledger minutes), working run at 3,000 neurons about 5-8 min (7-10 ledger minutes); idle-only month about 180 ledger minutes against the 1,000-minute allowance
- Backfill completion (embedded / total, stale count): PENDING (operator)
- Red run: new tests failed on import (`ModuleNotFoundError`), workflow/CLI tests errored, 7 CLI-contract help tests failed; three transport-failure tests failed red with `httpx.ReadTimeout`
- Deviations: no separate batching method (claim cap 50 = `EMBED_BATCH_LIMIT`); embedding price in its own table (a `NEURON_PRICES` row would break `known_models()` and `LLM_MODEL` validation); `stale` added to `DrainReport`/`Tally`; 409 on fail/release counted `skipped`; `embed drain` not recorded as a discovery run; CLI contract 22 -> 24 commands (`embed summary [--require-pending]`, `embed drain`); `--neuron-budget` default 3000; workflow not dispatched (file not on `main` yet), covered by a structural test
- Operator actions after merge: (1) secrets `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN` exist; (2) apply C3's migration to Supabase (`vector`, `unaccent`) and run the C4 backfill; (3) after release reaches `main`, dispatch `discovery-embed.yml` once, then set `DISCOVERY_EMBED_SCHEDULE=enabled`; (4) record first report, measured minutes and embedded/total here; (5) keep `EMBEDDING_MODEL` identical on Render and in the workers

### Chapter 7 — Web locale foundation

- Status: merged into loop branch (#376); refactor gate: smells found -> refactorings applied (`LocaleProvider` hooks extracted, `translate`/`lookup`/`interpolate`, formatter helpers); data-design gate: not applicable (web only)
- Bundle size before and after lazy loading: before `AppBootstrap` 715,529 B raw / 198.07 kB gzip, total JS 1.14 MB; after (de, en only) 716,552 B raw / 198,456 B gzip, no locale chunks. With five stand-in locale files: lazy `AppBootstrap` 716,961 B raw + five 12 KB chunks, vs eager 776,194 B raw / 204,007 B gzip (about 59 KB raw, 5.5 KB gzip kept out of entry per five locales).
- Parity test coverage (keys, placeholders, plurals): `de` and `en`, 367 keys each, 11 plural-family members, 0 problems; unit cases for missing/extra keys, placeholder mismatch, missing Slavic plural forms; enforces automatically when C11 adds locale files. Web locale list is checked against the API `SUPPORTED_LOCALES`.
- Fonts: Latin-ext for tr/pl/ro in Space Grotesk, Cyrillic (incl. ї є і ґ) via Inter fallback; checked in headless Chrome against the built CSS (not the running app)
- Deviations: locale query moved to `services/localesApi.ts` (provider ordering); inline `lang` script also reads browser language

### Chapter 8 — Hybrid query path

- Status: merged into loop branch (#386); refactor gate: smells found -> refactorings applied (`_nearest`/`_best_rows`/`_hits`/`_best_pool` extracted, `FusedSearch(retrieval, pool)` replaces paired optionals, `SearchPlan` NamedTuple, typed `Retrieval` decided in `SearchPlanner`); data-design gate: 4 `apply` (circuit breaker `CircuitBreakerQueryEmbedder`: 3 misses open it for 30 s then one probe; similarity cut-off moved out of the HNSW-ordered inner query via HAVING; pgvector < 0.8 silently ignores `hnsw.iterative_scan` so a version check falls back to an exact scan with a warning; neuron reservation commits in its own short transaction before the HTTP call; each with tests); accepted-risk: request waits on Workers AI (D1), httpx per-phase timeout not a hard deadline (trigger: embed p99 > 2x `QUERY_EMBED_TIMEOUT_S`), 0.1 neuron not refunded on failure, rate-limit counter per process (trigger: more than one API instance), legs evaluated twice for count and page; observed: `title_matches` seq scan over `jsonb_each_text`, **`tsv_native` built from `unaccent(text)` breaks Turkish suffix stemming (C16 should revisit; the query path mirrors the builder so they stay consistent)**
- `EXPLAIN` evidence (SYNTHETIC: 4,000 candidates, 28,000 search-text and embedding rows, 7 locales, `halfvec(1024)`, HNSW m=16 ef_construction=64, pgvector 0.8.7): keyword leg uses `BitmapOr` of both GIN indexes (de 6.5 ms, tr 10.8 ms at 28k rows); the planner picks an exact `Seq Scan` for the vector leg at this size (13.7 ms de, 16.1 ms tr); HNSW is used when forced (`Index Scan using ix_candidate_embedding_hnsw`, 2.3-5.3 ms), and `SEARCH_VECTOR_INDEX_ENABLED=false` forces exact. HNSW tuning is for C18. An HNSW-starvation test under a selective filter was inconclusive.
- Latency p50/p95 (SYNTHETIC, in-process, fake embedder; add about 359 ms per uncached live embedding call): browse 74/83 ms; browse + category 89/104; hybrid 123/153; hybrid + category 183/258; fallback keyword 96/136; fallback + category 163/255; legacy title match 81/95
- Fallback behaviour under timeout, error and exhausted budget: parametrised over timeout, HTTP 500, missing token, exhausted ledger, embedder returning None, plus ledger `OperationalError`: all 200 with `search_mode: "keyword"`, keyword hit present, vector-only hit absent; exhausted budget leaves the ledger unchanged; logs never contain the token or account id
- OpenAPI snapshot and web contract fixture regenerated: `CandidateCard.similarity` and `CandidateDetail.similarity` (nullable), `SearchMode` enum, required `CandidateListResponse.search_mode`; no web code changed
- Deviations: fusion is `UNION ALL` + `GROUP BY candidate_id` + `SUM(1/(k+rank))` rather than `FULL OUTER JOIN`; embedder split over six modules to stay near 100 lines; circuit breaker added (`QUERY_EMBED_BREAKER_FAILURES`, `QUERY_EMBED_BREAKER_COOLDOWN_S`); new settings `QUERY_EMBED_NEURONS` (0.1), `SEARCH_VECTOR_INDEX_ENABLED`, `SEARCH_RATE_LIMIT_PER_MINUTE` (30), `TRUSTED_PROXY_HOPS` (1); `LiveLimitMiddleware` reads the limit per request; blank `q` is browse; docs in `docs/operations/candidate-view.md` and `local-development.md`
- O12 (client IP for rate limiting): implemented as the `X-Forwarded-For` entry `TRUSTED_PROXY_HOPS` places from the right; the real proxy depth in front of Render is UNVERIFIED (operator check below), so O12 is not closed in `gaps-and-decisions.md`
- Operator actions after merge: (1) set `CLOUDFLARE_ACCOUNT_ID` and a Workers-AI-scoped `CLOUDFLARE_AI_API_TOKEN` on Render (O3); (2) after C3 migration, C4 backfill and the embed drain, set `SEARCH_HYBRID_ENABLED=true` (default `false` keeps today's title match); (3) verify the real client IP behind Render with a spoofed `X-Forwarded-For` and set `TRUSTED_PROXY_HOPS` and `SEARCH_RATE_LIMIT_PER_MINUTE`; (4) tune `QUERY_EMBED_TIMEOUT_S`, `SEARCH_MIN_SIMILARITY`, `SEARCH_FUSED_TOP_K` in C18

### Chapter 9 — Centred search and sort removal

- Status: pending
- Pinned default ordering (O6 resolution, combined score): pending
- Screenshots after (de, ru; desktop and mobile): pending

### Chapter 10 — Results presentation

- Status: pending
- `ScoreRing` shared by confidence and similarity; screenshots: pending
- `keyword` mode hint and omitted similarity ring: pending

### Chapter 11 — UI and taxonomy-label translation

- Status: pending
- Strings translated per locale; validator rejections and repairs: pending
- Neurons spent: pending
- Review manifest status per locale (machine / reviewed, reviewer, date): pending

### Chapter 12 — Combined ranking score

- Status: merged into loop branch (#392); refactor gate: smells found -> refactorings applied (`CardRepository` extracted from `cards.py` into `card_repository.py`; `search is None` branching in `CardRelations` replaced by a `CardSearch` protocol with `NoSearch` and `FusedSearch` variants in `card_search.py`; interim `by_relevance` ordering and the old `None` sort branch deleted); `_by_combined` keeps two arms (browse versus search), split on a third ranking mode; data-design gate: applies, no `apply` findings; accepted-risk: offset paging re-evaluates the pool per request so rows written between pages can shift (trigger: duplicate or missing rows reported in practice); observed: ordering uses the unrounded score while cards show four decimals, so equal displayed scores may be ordered by the tail
- Default weight and the SQL/Python agreement result: `SEARCH_CONFIDENCE_WEIGHT` default 0.3, validated 0..1 at load and in the expression; `test_search_scoring.py` checks SQL versus Python agreement on a grid and rejects an out-of-range weight; rollback is `SEARCH_CONFIDENCE_WEIGHT=0` (pure relevance). Tuning is chapter 18 (O14)
- Browse regression result: browse order unchanged (confidence, completeness, mentions, tie-break); `score` equals confidence to within 5e-5 outside a search, so browse and legacy title-match tests compare with a tolerance
- OpenAPI snapshot and contract fixture regenerated: `apps/web/src/test/contract/openapi.schemas.json` gained `score` on `CandidateCard` and `CandidateDetail`; no web code changed. Run counts: API 1965 passed and 25 skipped, web 1131 passed and 1 expected fail
- Incident (reported by the implementer): one early `pytest` run in `apps/api` was launched without a scratch `DATABASE_URL`, followed the `apps/api/.env` symlink and hung; it was killed. Same unverified risk as the chapter 13 incident; every later run used an inline scratch URL

### Chapter 13 — Translation schema and core

- Status: merged into loop branch (#378); live probe complete for all six locales; D13 decided (Cloudflare PoC); native-speaker spot checks PENDING (manual). Refactor gate: smells found -> refactorings applied (error-category table, `_reserve_neurons`, answer parsing and validators split, `use_ledger` flag removed, provider leak out of probe). Data-design gate: no `apply` findings (accepted-risk: index row is the only key index since `ObjectStore` has no `list`; no CHECK constraints on hash widths; observed: prompt/glossary version not pinned in payload (D10), `translation_task` completed-row retention for C14/C15)
- Migration id and round-trip result: `20261111_translation_schema` (parent `20261110_search_schema`); `check_migrations.sh` passes (single head, upgrade, downgrade -1, upgrade, `alembic check` clean). Reuses `work_task_status`; adds `translation_source`.
- Engine port, registry and conformance suite: `llm` adapter passes `translation_engine_contract.py`; three deliberately broken fakes (dropped unit, mangled placeholder, leaked token) each fail their own check; a fake characters-unit adapter registers with no other changes; `meter_for_unit("characters")` raises "no meter for unit characters". No MT adapter added (the probe decides).
- Translation object store round trip: in-memory and S3 (moto) pass write/read/delete/missing; key `translations/v1/{candidate_id}/{locale}/card/{content_sha256}.json`; canonical sorted-key UTF-8 JSON; key sha256 and `size_bytes` match the bytes; a re-translation gets a new key.
- Probe reports per locale and engine (2026-11-10, chief of staff, live, `llm` / `@cf/qwen/qwen3-30b-a3b-fp8`, 50 real cards sampled via the public API; reports and sheets in the gitignored `apps/discovery-ingest/translation-probe/`):

  | locale | validated ok | pass rate | failures | neurons spent | neurons per card | projected neurons, whole corpus (4,713 cards) |
  | --- | --- | --- | --- | --- | --- | --- |
  | tr | 42/50 | 0.84 | glossary 7, numbers 1 | 600 | 12.0 | 56,534 |
  | en | 43/45 | 0.86 | numbers 1, glossary 1, unusable output 5 | 463 | 10.3 | 48,472 |
  | uk | 41/50 | 0.82 | numbers 3, glossary 6 | 647 | 12.9 | 60,974 |
  | pl | 46/50 (rerun; first attempt stopped at 15/20 on a Workers AI timeout) | 0.92 | glossary 3, numbers 2 | 577 | 11.5 | 54,381 |
  | ru | 40/50 (rerun; first attempt hit a candidate-API read timeout) | 0.80 | glossary 8, numbers 3 | 593 | 11.9 | 55,850 |
  | ro | 49/50 | 0.98 | glossary 1 | 648 | 13.0 | 61,093 |

  About 337k neurons for all six locales (sum of the per-locale projections), which is about 35 days at the 9,500-neuron daily share. Pass rates 0.80 to 0.98; glossary adherence and number preservation are the main failures. The probe calls Workers AI outside the ledger; about 3,800 neurons were spent today on these runs (including one aborted `pl` run), plus about 9 on the C1 embedding probe. All six locales have now been probed.
- Environment notes for running the probes behind the corporate proxy: Python's certificate store rejects the proxy's certificate, so export `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` (verification stays on); the Supabase database is not reachable from this network (so the incident below most likely only hung on connect). `apps/api/.env` is now a symlink to `~/.config/redtape/probe.env`, which was merged with the keys that only the old `.env` had; the originals are saved as `~/.config/redtape/api.env.pre-symlink` and `probe.env.bak`. Because the symlinked `.env` still holds `DATABASE_URL`, implementers must keep overriding `DATABASE_URL` with a scratch database for tests.
- Native-speaker spot-check notes: pending. Sheets: `translation-probe/llm-<L>.csv`. The glossary renderings for the six locales were drafted by the implementer and need native review.
- Engine decision (D13): Cloudflare `llm` adapter for the PoC, Azure later (recorded in `gaps-and-decisions.md`). Open consequence: the full corpus in six locales does not fit a free-tier pace; coverage must be priority-limited (C14/C15) and the locale list may need narrowing before the first drain is enabled.
- Incident (reported by the implementer): one early `pytest` run in `apps/api` started without a scratch `DATABASE_URL`, hung about 2 min and was killed. `Settings` loads `apps/api/.env`, and `tests/conftest.py` runs `CREATE EXTENSION IF NOT EXISTS` and `Base.metadata.create_all` on the configured database. If that `.env` points at Supabase and the connection succeeded, tables or extensions may have been created outside Alembic. Unverified; check with the SQL in the orchestration notes.

### Chapter 14 — Translation queue and machine API

- Status: merged into loop branch (#384); refactor gate: smells found -> refactorings applied (`_refuse` dispatch table, `_store_text` split, `plan.py` extracted, `QueueCounts`, `fail`/`release` shared in `search/leased_settle.py`, `OPEN_TASK_PREDICATE`, `scripts/backfill_common.py`); data-design gate: no `apply` findings (lock order candidate share lock -> task lock -> index row, mutation-checked; blob written before index row); accepted-risk: R2 puts inside `complete` hold locks (trigger: mention-route lock waits or R2 put p95 > ~1 s), orphan objects after failed delete (trigger: bucket bytes vs sum of index `size_bytes`), same-key zombie and replayed `complete` answers `rejected`, mention-batch fan-out of up to 600 upserts; observed: `unavailable` carries no `not_before` (C15 must stop on it), completed/failed tasks never pruned, staleness only via the `record_mentions` hook, a `TRANSLATION_UNIT_RECIPE_VERSION` bump needs a backfill (C18 runbook), **C5 `EmbeddingCompletion` locks task then search-text row `FOR SHARE` while writers lock search text then task: inverse order, possible deadlock (not changed here)**, future human-edit endpoint (O15) PK conflict, R2 ledger reserve shares the request transaction
- Backfill counts (enqueued, up to date, stale): scratch DB only, synthetic (41 candidates, 6 locales): run 1 `enqueued=209 up_to_date=30 stale=18 missing=191 human_protected=1 no_source=6`; run 2 `enqueued=0` (idempotent). Real counts PENDING (operator)
- Object-store outage test (task handed back, attempt not burned): store `None` and `ObjectStoreQuotaError` on put both give `unavailable`, task back to `pending`, `attempt_count == 0`, no index row; a failure after the put leaves one orphan object
- Priority ordering evidence (high-confidence first, all locales together): claim orders by priority, candidate id (new optional `LeasedQueue.claim(grouping=...)`), age, id; scratch-corpus claim of 25 went candidate by candidate in descending confidence with all locales together; re-translations (priority >= 10000) sort last; mutation-checked
- Contract fixture regenerated: `discovery_machine_contract.json` (+5 routes, 13 models, `TranslationOutcome`) and web `openapi.schemas.json`
- Deviations: claim scoped to current `TRANSLATION_TARGET_LOCALES` (empty list claims nothing); `human_exists` completes its task, a bounds failure fails permanently; `CandidateService` takes a 4th constructor argument (`TranslationEnqueuer`); `validate_i18n_value` made public (validators reject, not strip, control characters); local CI ran a copy of `ci.sh` with scratch DB names because the original drops the shared `redtape_migrations`/`redtape_pytest` databases and an auto-mode check denied it
- Operator actions after merge: (1) narrow `TRANSLATION_TARGET_LOCALES` on Render and in worker settings before the first backfill (D13); (2) after deploy run `uv run python -m scripts.backfill_translations` in `apps/api` against production and record counts; (3) confirm R2 object-store variables on Render (without them every `complete` answers `unavailable`)

### Chapter 15 — Translation drain worker

- Status: merged into loop branch (#388); refactor gate: smells found -> refactorings applied (`FlooredMeter` moved to `worker/floored_meter.py` with `_recheck` extracted, `_drain` extracted from `run_translate_drain`, `CountedTranslator` moved to `translate_drain.py`; shared lease settlement in `lease_settle.py`, embed drain imports it); data-design gate: no `apply` findings; accepted-risk: the query-embedding floor is check-reserve-recheck, so a concurrent query-embedding spend can slip between the two ledger reads (an atomic floor needs a chapter 14 API change; revisit if the floor is breached in production; the ledger hard cap stays atomic and the `discovery-pipeline` concurrency group serialises drains)
- Notes: work was cherry-picked from an earlier unpushed attempt (`wip/c15-prior-attempt`, left in place locally) and re-verified; `mypy .` as written in the chapter's verification block reports 410 errors, all in `tests/` (not checked against the loop branch before this chapter); `./ci.sh` and the workflow run `mypy discovery_ingest`, which is clean
- Operator actions after merge: run the chapter 14 backfill; narrow `TRANSLATION_TARGET_LOCALES` on Render (D13); set `DISCOVERY_TRANSLATE_SCHEDULE=enabled` (optional `TRANSLATION_ENGINE`, `QUERY_EMBED_RESERVE`) with secrets `CLOUDFLARE_AI_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; confirm R2 variables on Render; dispatch once. Cadence as shipped: daily 17:10 UTC, 2500-neuron run cap, 1000-neuron floor, 10 tasks per batch, at most 60 batches, 600 s. Minutes per run not yet measured
- First drain report (claimed, stored, stale, rejected, neurons): pending
- Validator failure and repair rate: pending
- Cadence, query-embedding floor and Actions minutes per run: pending
- Translated / total per locale: pending

### Chapter 16 — Translated text in search text and embedding tasks

- Status: merged into loop branch (#390); refactor gate: smells found -> refactorings applied (`run_prune` split into `_vector_totals` and `_delete_open_tasks`; duplicated embedding fixtures replaced by the shared `embed`/`add_embedding` helpers); `backfill_search.py` is 133 lines, left as is (split on a third backfill mode); data-design gate: no `apply` findings, no schema change; accepted-risk: (1) lock order inverse to embedding `complete` (search text then task versus task then search text) can deadlock, one side aborts, the subscriber's savepoint keeps the translation stored and a backfill reconciles (trigger: "deadlock detected" on `embedding_task` or `candidate_search_text`); (2) `EMBEDDING_LOCALES` gates enqueue only, claim does not consult it, so pending tasks of a dropped locale keep draining (drop from the setting, then prune; trigger: embedding neurons spent on a dropped locale); observed: a subscriber failure is only logged, so a locale's search text stays missing until `backfill_search --locale` runs
- Deviations: subscriber registered in `translation/router.py` instead of `translation/service.py` (keeps `TranslationCompletion` free of search imports); reclaimed figure is stored vector bytes (`pg_column_size` sum), the table and HNSW index only give space back after a vacuum
- Operator actions after merge: once the translate drain has data run `python -m scripts.backfill_search --locale <code>` in `apps/api` per translated locale; run the embed drain until empty; set `EMBEDDING_LOCALES` on Render if narrowing (prune only after removing the locale from the setting)
- Per-locale search-text rows, embedded counts and stale counts: pending
- Table and index sizes per locale versus budget: pending
- Polish and Ukrainian keyword behaviour (O9): pending

### Chapter 17 — Translation read path and pop-over

- Status: pending
- Query-count test (constant per page) and zero object-store calls on a list page: pending
- R2 reads for one pop-over open, and `304` on revalidation without a store read: pending
- Screenshots (trigger, open pop-over, stale note, phone width; `tr`, `ru`): pending
- Pop-over network check (one stored-text request on first open, none on second open, no model call): pending

### Chapter 18 — Evaluation, tuning and rollout

- Status: pending
- Golden set size per locale: pending
- Recall@10, MRR and nDCG@10 per configuration and locale, with and without translated rows: pending
- Chosen `SEARCH_CONFIDENCE_WEIGHT`, `RRF_K`, similarity cut-off, top-N, HNSW parameters: pending
- Locales that keep vectors and storage reclaimed (O10): pending
- Similarity ring band thresholds (O7): pending

## Post-deploy validation

| Check | Expected | Recorded |
| --- | --- | --- |
| `GET /api/v1/candidates?q=…` with the flag off | `search_mode: "keyword"`, legacy behaviour | pending |
| Same with the flag on | `search_mode: "hybrid"`, similarity and score present | pending |
| Query with the embedder token removed | `search_mode: "keyword"`, HTTP 200 | pending |
| `Accept-Language: tr` list | `translation` summary present for translated candidates, `null` for `de` readers | pending |
| `GET /api/v1/candidates/{id}/translation?locale=tr` | stored text with `ETag`; `304` on revalidation | pending |
| Queue summaries (embeddings, translations) | `pending_ready` near 0 after the drains | pending |
| Neuron ledger | Query-embedding floor intact after a translate run | pending |
| Database size | under `DB_SOFT_LIMIT_BYTES` with margin (baseline about 83 MB) | pending |
| Object storage | translation objects and bytes; R2 Class A and B usage under the caps | pending |
| Locale served | only enabled locales appear in `GET /locales` | pending |
| `human` translations | none overwritten (query recorded) | pending |

**Last orchestration:** 2026-11-11 — resumed; chapter 12 merged (13 of 18: C1, C2, C3, C7, C4, C13, C5, C6, C14, C8, C15, C16, C12); next in order: C9
