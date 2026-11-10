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

- Status: pending
- Contract fixture regenerated: pending
- Claim concurrency test (two claimers, no overlap): pending
- Generic leased queue extraction; existing discovery queue tests unchanged: pending

### Chapter 6 — Embedding drain worker

- Status: pending
- First drain report (claimed, completed, stale, neurons): pending
- Cadence chosen and Actions minutes per run: pending
- Backfill completion (embedded / total, stale count): pending

### Chapter 7 — Web locale foundation

- Status: merged into loop branch (#376); refactor gate: smells found -> refactorings applied (`LocaleProvider` hooks extracted, `translate`/`lookup`/`interpolate`, formatter helpers); data-design gate: not applicable (web only)
- Bundle size before and after lazy loading: before `AppBootstrap` 715,529 B raw / 198.07 kB gzip, total JS 1.14 MB; after (de, en only) 716,552 B raw / 198,456 B gzip, no locale chunks. With five stand-in locale files: lazy `AppBootstrap` 716,961 B raw + five 12 KB chunks, vs eager 776,194 B raw / 204,007 B gzip (about 59 KB raw, 5.5 KB gzip kept out of entry per five locales).
- Parity test coverage (keys, placeholders, plurals): `de` and `en`, 367 keys each, 11 plural-family members, 0 problems; unit cases for missing/extra keys, placeholder mismatch, missing Slavic plural forms; enforces automatically when C11 adds locale files. Web locale list is checked against the API `SUPPORTED_LOCALES`.
- Fonts: Latin-ext for tr/pl/ro in Space Grotesk, Cyrillic (incl. ї є і ґ) via Inter fallback; checked in headless Chrome against the built CSS (not the running app)
- Deviations: locale query moved to `services/localesApi.ts` (provider ordering); inline `lang` script also reads browser language

### Chapter 8 — Hybrid query path

- Status: pending
- `EXPLAIN` for vector leg (HNSW used) and keyword leg (GIN used): pending
- Latency p50/p95, hybrid and fallback: pending
- Fallback behaviour under timeout, error and exhausted budget: pending
- OpenAPI snapshot and web contract fixture regenerated: pending

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

- Status: pending
- Default weight and the SQL/Python agreement result: pending
- Browse regression result: pending
- OpenAPI snapshot and contract fixture regenerated: pending

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

- Status: pending
- Backfill counts (enqueued, up to date, stale): pending
- Object-store outage test (task handed back, attempt not burned): pending
- Priority ordering evidence (high-confidence first, all locales together): pending
- Contract fixture regenerated: pending

### Chapter 15 — Translation drain worker

- Status: pending
- First drain report (claimed, stored, stale, rejected, neurons): pending
- Validator failure and repair rate: pending
- Cadence, query-embedding floor and Actions minutes per run: pending
- Translated / total per locale: pending

### Chapter 16 — Translated text in search text and embedding tasks

- Status: pending
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

**Last orchestration:** 2026-11-10 — stopped after chapter 13 and the C13 live probes by user request (6 of 18 merged: C1, C2, C3, C7, C4, C13); next in order: C5
