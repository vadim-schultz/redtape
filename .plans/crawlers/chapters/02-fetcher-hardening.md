---
name: "Chapter 2 — Fetcher hardening"
overview: "Make the worker's HTTP fetcher follow redirects safely, identify itself, honour robots.txt, cap body size, refuse private addresses, and classify failures as retryable or not."
todos:
  - id: redirects
    content: "Follow up to five redirects manually, validating every hop, and report the final URL"
    status: pending
  - id: politeness
    content: "Identifying User-Agent and per-host robots.txt with a cache"
    status: pending
  - id: limits
    content: "Body size cap and private-address / scheme guard"
    status: pending
  - id: classify
    content: "Classify outcomes as retryable or permanent"
    status: pending
  - id: drain-workflow
    content: "Add a manual discovery-drain.yml workflow for live gates"
    status: pending
isProject: false
---

# Chapter 2 — Fetcher hardening

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-fetcher-hardening` · **Status:** planned

**Depends on:** [01](01-ingest-ci.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Production data shows seven fetches with status 301, 302 or 307 recorded as completed, two 403 responses with a 12-byte body, and one connection reset and one timeout. [fetcher.py](../../../apps/discovery-ingest/discovery_ingest/worker/fetcher.py) uses httpx defaults (no redirect following), sends the library User-Agent, ignores robots.txt, has no size cap, and returns every status below 400 as success. The same fetcher serves `fetch_url` and the FIM `enrich_metadata` call, so the fix must stay generic.

## Contract

`PoliteUrlFetcher.get(url)` returns a `FetchOutcome` that gains:

- `final_url: str | None`, the URL after redirects;
- `redirect_count: int`;
- `retryable: bool`, true for timeout, connection error or reset, HTTP 429 and 5xx; false otherwise.

Behaviour:

1. **Redirects.** Follow `301/302/303/307/308` manually, at most five hops, so every hop is validated before it is requested. More than five, or a loop, is a permanent failure with an explicit message. A 3xx that cannot be resolved (no `Location`) is a failure, never a success.
2. **Safety.** Only `http` and `https`. Resolve the host and reject loopback, private, link-local, multicast and reserved addresses on every hop, using the standard `ipaddress` module. Rejection is a permanent failure.
3. **Identity.** A fixed `User-Agent`: `RedtapeBot/1.0 (+<contact URL>)`. The contact URL comes from ingest settings with a default of the repository URL; the value is read once in `IngestSettings`, not scattered.
4. **robots.txt.** Per host, fetched once per run through the same client and parsed with `urllib.robotparser`; cached for the process. 404/410 and other 4xx mean "allowed"; a 5xx or timeout on `robots.txt` makes that host retryable for this run (skipped, not fetched); a disallow is a permanent failure with the message `robots.txt disallows`. The per-host minimum interval is unchanged and also applies to the `robots.txt` request.
5. **Size cap.** Stream the response and stop at `max_bytes` (default 5 MB, constructor argument). Exceeding it is a permanent failure and the partial body is discarded.
6. **No evasion.** A 403 is recorded as a failure. The fetcher does not rotate agents, spoof headers, or retry around blocks.

`FetchLogAppendRequest` is unchanged in this chapter: the worker keeps writing `http_status`, `content_type`, `byte_length` and `error_message`; `final_url` and `retryable` are consumed by chapters 4 and 15.

`fetch_url` and `enrich_metadata` treat the new failure outcomes through the existing `fail_task` path. A manual workflow makes live gates possible:

`.github/workflows/discovery-drain.yml` (`workflow_dispatch` only in this chapter) with inputs `max_tasks` (default 50), `max_batches` (default 1) and `time_budget_seconds` (optional); installs the ingest package, waits for API health with `discovery_ingest.health.wait_for_api`, runs `python -m discovery_ingest worker drain ...`, and writes the JSON drain report to the job summary. It uses the `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` secrets only.

## TDD loops

All tests use `httpx.MockTransport`; no real network. New file `apps/discovery-ingest/tests/test_worker_fetcher.py`.

### Loop A — Redirects

**Red**

1. `fetcher follows a 301 to a 200 and reports the final url` — assert status 200, `final_url`, `redirect_count == 1`.
2. `fetcher fails after more than five redirects` — assert permanent failure and no body.
3. `fetcher never reports an unresolved 3xx as success` — missing `Location` yields a failure outcome.

**Green:** a small hop loop that resolves relative `Location` values against the current URL.

**Refactor:** keep the loop body at one level of nesting; extract `_next_url` and `_validate_hop`.

### Loop B — Politeness

**Red**

1. `fetcher sends the identifying user agent` — assert the header on both the page and `robots.txt` requests.
2. `fetcher skips a path disallowed by robots.txt` — assert no page request was made and the message names robots.
3. `fetcher treats a missing robots.txt as allowed` — 404 allows; a 503 yields a retryable skip.

**Green:** a `RobotsCache` collaborator with injected clock-free logic.

**Refactor:** the cache owns parsing; the fetcher only asks `allowed(url)`.

### Loop C — Limits and guards

**Red**

1. `fetcher aborts a response larger than the cap` — assert failure and `body is None`.
2. `fetcher rejects private and loopback addresses` — including a redirect that points at `127.0.0.1`.
3. `fetcher rejects non-http schemes` — `file:` and `ftp:`.

**Green:** a pure `is_public_address(host_ip)` helper and a streaming read with a byte counter. Resolution is injected so tests do not touch DNS.

**Refactor:** isolate address resolution behind a one-method protocol.

### Loop D — Classification

**Red**

1. `fetcher marks timeouts resets 429 and 5xx retryable` — table-driven.
2. `fetcher marks 404 403 and robots denials permanent` — table-driven negative.

**Green:** one `classify(outcome) -> bool` function; no scattered conditionals.

**Refactor:** confirm `drain._handle_fetch_url` and `enrich_metadata` call the same failure predicate.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_worker_fetcher.py tests/test_worker_drain.py tests/test_enrich_metadata_worker.py
gh pr checks --watch
gh workflow run discovery-drain.yml -f max_tasks=50 -f max_batches=1
gh run watch
```

Live gate: after the operator runs the repair in [chapter 22](22-operator-manual-steps.md) (step S11, which re-pends the tasks whose fetch log recorded a 3xx), a dispatch drain must show those tasks either completed with a 200 or failed with an explicit reason; none may remain completed with a 3xx. Record the run ID.

## Out of scope

Retrying (chapter 4), storing bodies (chapter 15), reading `Crawl-delay`, per-host concurrency, proxies, JavaScript rendering.
