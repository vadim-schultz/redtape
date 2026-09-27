---
name: "Chapter 3 — Polite fetcher"
overview: "PoliteFetcher checks robots.txt, rate-limits per host, sets a real user agent and retries only on transient failures, tested against respx with no real network access."
todos:
  - id: robots
    content: "robots.txt check, cached per host"
    status: pending
  - id: fetcher
    content: "PoliteFetcher.get with rate limit, timeout and retry"
    status: pending
isProject: false
---

# Chapter 3 — Polite fetcher

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-fetcher` · **Status:** planned

**Depends on:** [1](01-crawler-package-skeleton.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Every page the crawler fetches goes through one path that respects `robots.txt`, never hammers a host, and
identifies itself honestly — the ethics-and-compliance concern the `crawlers-jobs` strand names explicitly.

## Design decisions

**`RobotsCache`**: `urllib.robotparser.RobotFileParser` per host, fetched once and cached for the run's
lifetime (not per-request); `can_fetch(user_agent, url) -> bool`. A host with no `robots.txt` (404) is
treated as allow-all (standard interpretation); a host that errors fetching `robots.txt` is treated as
**disallow** (fail closed, not open — the opposite default from a missing file, and worth a comment where
it is coded since the two failure modes look similar but must behave oppositely).

**Rate limiter ported from `openplz_client.py`**: the same `_RateLimiter` shape
([openplz_client.py](../../../apps/api/app/services/openplz_client.py)), per-host this time (a dict of
limiters keyed by host, not one global limiter — different sources may be different hosts entirely).

**`PoliteFetcher.get(url) -> httpx.Response`**: checks robots, waits for the rate limiter, sends the
request with the fixed `User-Agent` (architecture §4), retries via the shared `retry` helper (chapter 2) on
timeout/5xx only, raises `RobotsDisallowedError` (not retried, not a transient failure) when disallowed.

**Timeout and rate**: constructor parameters with sane defaults (10s timeout, 1 request/second/host),
overridable per source later if a real source needs it (not built until needed).

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/crawler/robots.py` | `RobotsCache` |
| `apps/crawler/crawler/rate_limiter.py` | `RateLimiter` (ported) |
| `apps/crawler/crawler/fetcher.py` | `PoliteFetcher`, `RobotsDisallowedError` |
| `apps/crawler/tests/test_fetcher.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `RobotsCache · allows a path robots.txt does not disallow` | Positive |
| `RobotsCache · disallows a path robots.txt disallows` | Negative |
| `RobotsCache · a missing robots.txt (404) allows fetching` | Standard interpretation |
| `RobotsCache · a robots.txt fetch error disallows fetching` | Fail closed |
| `RobotsCache · fetches robots.txt at most once per host across many checks` | Cache proof |
| `PoliteFetcher.get · raises RobotsDisallowedError without making the page request` | No second respx call recorded |
| `PoliteFetcher.get · sends the configured User-Agent` | Header |
| `PoliteFetcher.get · waits between two requests to the same host` | Timing assertion with a fake clock |
| `PoliteFetcher.get · does not wait between requests to different hosts` | Negative pair |
| `PoliteFetcher.get · retries a 503 then succeeds` | Two respx calls |

## Green

1. `RobotsCache`; tests 1–5.
2. Rate limiter port; tests 8–9 (unit, no HTTP).
3. `PoliteFetcher` composing both plus the shared `retry`; tests 6, 7, 10.

## Refactor gate

`PoliteFetcher.get` composes three named steps (`_check_robots`, `_throttle`, `_request`), each ≈5 LOC.
Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_fetcher.py -m "not needs_playwright"
```

## Out of scope

Extraction (chapter 5), the source registry telling the fetcher what to fetch (chapter 4).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-fetcher
```

```text
test(crawler): describe robots.txt handling, rate limiting and retries

feat(crawler): add PoliteFetcher
```
