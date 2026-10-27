---
name: "Chapter 18 — First page extractor"
overview: "Choose the first host from real snapshots, build its extractor against saved markup, register it, and run it live."
todos:
  - id: choose
    content: "Capture snapshots from the top hosts and decide which has stable document content"
    status: pending
  - id: fixtures
    content: "Commit sanitized listing and edge-case fixtures"
    status: pending
  - id: extractor
    content: "Implement, version and register the extractor"
    status: pending
  - id: live
    content: "Run fetch then extract live and review the candidates"
    status: pending
isProject: false
---

# Chapter 18 — First page extractor

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/crawlers-first-extractor` · **Status:** planned, **optional** (revised 2026-10-26)

**Depends on:** [17](17-extractor-framework.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Status: optional

The [extraction](../../extraction/00-architecture.md) suite is now the primary page extractor: one Cloudflare Workers AI call per rendered snapshot, validated and grounded, covers all 123 hosts without per-host selectors. This chapter is kept for hosts where its eval (extraction chapter E5) shows the LLM is weak, or where a deterministic extractor is wanted for precision and zero neurons. Chapter 20's live gate then uses a candidate from the LLM path. If this chapter is skipped, nothing downstream breaks: chapter 17's registry stays empty.

## Goal

Prove the whole page path on one real host. The choice is made from data, not assumed: 2026-10-23 task counts by host were `verwaltung.bund.de` 432, `fimportal.de` 137, `www.arbeitsagentur.de` 132, `serviceportal-uv.dguv.de` 76 and `bundesportal.gkv-spitzenverband.de` 66, across 123 hosts in total.

## Step 0 — Choose the host (blocking)

1. After chapter 15's live gate and the S14 re-pend, drain fetch tasks, then run `discovery-render.yml` about four times. The render queue is throttled by Cloudflare's free plan (about 4 pages a minute, so 55 to 65 pages in a 900-second run, chapter 15), but the top hosts make up roughly 30, 10 and 9 percent of the tasks, so about 240 rendered pages are enough to hold five snapshots for each of them.
2. Run `discovery-fixture-capture.yml` for the three most frequent hosts (five snapshots each) and download them.
3. Inspect: does the page list required documents, forms or evidence in stable markup? Landing pages and login pages do not qualify. A JavaScript shell (likely for `fimportal.de/detail/...`) is **not** disqualified any more, because the snapshot is the rendered DOM: judge the markup the snapshot contains, not the raw response.
4. Record the decision and its evidence in the ledger. If no top host qualifies, record the negative finding in [gaps-and-decisions.md](../gaps-and-decisions.md), pick the best candidate from the next hosts, and keep PVOG payload harvest (chapter 7) as the primary source. A negative result is a valid outcome of this chapter.

## Contract

- `discovery_ingest/extract/<host_slug>.py` implements the `Extractor` protocol with `id`, `version = "1"`, `matches` by exact host (and path prefix when pages differ in shape), and `extract` building `MentionItem`s with `role`, `excerpt`, `source_field` (a CSS-path-like locator) and absolute `official_url` for linked forms.
- Relative links resolve against `final_url`. Items with no usable title are skipped and counted in a returned diagnostic (logged, not raised). Duplicates within a page collapse.
- The extractor is added to `EXTRACTORS` in `registry.py`.
- Politeness is inherited from the fetcher and the render step; the extractor itself makes no network calls.
- Fixtures live in `apps/discovery-ingest/tests/fixtures/html/<host_slug>/{listing,edge-case}.html`: real markup with personal data removed and size trimmed. The edge case is something actually observed (an item without a link, a relative URL, an empty list).

## TDD loops

### Loop A — Extraction

**Red** (`apps/discovery-ingest/tests/test_extractor_<host_slug>.py`)

1. `extractor matches its host and rejects other hosts and non-html`.
2. `extractor returns the expected mentions for the listing fixture` — exact titles, roles, absolute urls.
3. `extractor skips unusable items and reports them in the diagnostic` — edge-case fixture.
4. `extractor returns nothing for an unrelated page` — negative fixture.
5. `extractor output is deterministic and deduplicated`.

**Green:** the smallest parser that satisfies the fixtures. **Refactor:** selectors as named constants; helper per concern; no nesting beyond one level.

### Loop B — Wiring

**Red** `registry contains the extractor and the after-snapshot hook enqueues extract_page for a matching snapshot and not for another host`. **Green/Refactor:** registration only.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_extractor_<host_slug>.py tests/test_extract_registry.py tests/test_extract_worker.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
gh workflow run discovery-drain.yml -f kinds=fetch_url -f max_tasks=50 -f max_batches=2   # enqueues render_page
gh workflow run discovery-render.yml -f max_tasks=5 -f max_batches=4                       # snapshots, then extract tasks are enqueued
gh workflow run discovery-drain.yml -f kinds=extract_page -f max_batches=2
gh run view --log
```

Live gate: the second drain completes `extract_page` tasks; the admin Documents list shows new candidates with `extractor` set to this extractor; a reviewer reads ten mentions against their source pages and records the precision observed (for example "8 of 10 are real documents") in the ledger. If precision is poor, bump the extractor version after fixing and let the version-keyed enqueue re-run it.

## Out of scope

More hosts (each is a new chapter-18-shaped task), crawling beyond catalogue URLs, PDF forms, LLM extraction.
