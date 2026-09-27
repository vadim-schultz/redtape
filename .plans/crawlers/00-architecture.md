---
name: Crawlers — Architecture
overview: "A separate apps/crawler package that fetches configured sources politely, extracts document candidates per source, captures a screenshot as evidence, and submits both as a suggestion through the API — running as scheduled GitHub Actions jobs, never with direct database access."
isProject: false
---

# Crawlers — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

Every earlier suite in this program exists to receive what a crawler produces:
[suggestion-interface](../suggestion-interface/00-architecture.md) accepts machine submissions,
[evidence-storage](../evidence-storage/00-architecture.md) stores proof, [auth](../auth/00-architecture.md)
gives crawlers an identity, [voting-moderation](../voting-moderation/00-architecture.md) decides what
survives. This suite is the producer.

It implements the **discovery** mode from the
[`crawlers-jobs` strand](../../docs/planning/directions/crawlers-jobs/README.md): broad crawling that
proposes new documents into the review queue. The strand's other mode, **freshness** (re-checking existing
documents' links and metadata), is a deliberate non-goal here — see
[gaps-and-decisions.md](gaps-and-decisions.md).

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Source** | One configured place to crawl: a jurisdiction, a start URL, an extractor id. |
| **Extractor** | Code that turns one fetched page into zero or more `DocumentCandidate`s. One per source shape (a government portal's list page, say). |
| **Candidate** | A `DocumentCandidate`: title, URL, optional description — not yet a suggestion until submitted. |
| **Run** | One execution of the orchestrator over some or all sources, producing a report. |

## 3. Package layout

A new top-level app, **not** inside `apps/api`, because it has its own dependencies (Playwright, a browser
binary) that the API image should never carry:

```
apps/crawler/
  pyproject.toml
  crawler/
    api_client.py        # talks to the suggestion and evidence API, never the database
    fetcher.py           # polite HTTP: robots.txt, rate limit, timeout, retries
    sources.py            # loads and validates the source registry
    extractors/
      base.py             # Extractor protocol -> DocumentCandidate
      <source>.py          # one real extractor (chapter 6)
    screenshot.py          # Playwright capture
    run.py                 # orchestrator CLI
  tests/
  sources.yaml
```

**No database import anywhere in `apps/crawler`.** Every write goes through the suggestion and evidence
HTTP APIs with an API key (auth chapter 7–8), exactly like any other machine client — the crawler is not a
privileged internal component, it is the first real user of the public machine interface, which is the
point of building that interface first.

## 4. Fetching

`PoliteFetcher`: checks `robots.txt` (cached per host, `urllib.robotparser`), enforces a per-host rate limit
(reusing the `_RateLimiter` shape already proven in
[openplz_client.py](../../apps/api/app/services/openplz_client.py), ported here since the crawler is a
separate package and should not depend on `apps/api`), a fixed `User-Agent` identifying the project and a
contact URL, timeouts, and a small retry budget on 5xx/timeout only (never on 4xx). Uses `httpx` (new
dependency for this package; the API package deliberately stays on `urllib` for its one existing client, no
change there).

## 5. Extraction

`Extractor` protocol: `matches(source) -> bool`, `extract(html, source) -> list[DocumentCandidate]`. A
registry (`EXTRACTORS: list[Extractor]`) picks the first match per source — same dispatch-table discipline
as the API's suggestion-kind handlers, applied here to extraction strategy instead of payload kind.

## 6. Screenshot capture

Playwright (Chromium, headless), one full-page PNG per successfully extracted candidate's source page,
`fetched_at` set to the capture instant. Playwright is heavy (a browser download); it runs only in the
scheduled job, never in unit tests (fixtures and fakes cover extraction and submission logic; screenshot
capture gets a small number of integration tests gated behind a marker, run only in CI where the browser is
installed).

## 7. Submission

For each candidate: `POST /api/v1/suggestions` (`kind=new_document`, `source_type` derived from the API key,
`Idempotency-Key` = a stable hash of `source_url` so re-running a job is safe), then on success
`POST /api/v1/suggestions/{id}/evidence` with the screenshot. A 409 (duplicate) is logged and skipped, not
treated as a failure — it means the candidate is already known.

## 8. Scheduling

A GitHub Actions workflow, modeled on
[openplz-import.yml](../../.github/workflows/openplz-import.yml): scheduled plus `workflow_dispatch`
(with a `sources` input to run a subset), installs Playwright's browser in the job, holds the crawler's API
key as a repository secret, calls `python -m crawler.run`.

## 9. Out of scope

Freshness/link-health crawling (the strand's other mode), JavaScript-rendered extraction beyond what
Playwright's page load already provides, PDF parsing, a worker process or queue (GitHub Actions is the
runtime, per program decision D3), CAPTCHA or anti-bot handling, more than one extractor at first ship.
