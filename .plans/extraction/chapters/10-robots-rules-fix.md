---
name: "Chapter E10 — Robots rules fix"
overview: "Replace urllib's robots.txt matching with an RFC 9309 matcher (longest match wins, Allow wins ties, * and $ supported) so the crawler neither skips allowed pages nor fetches forbidden ones; executes right after E11 (before E1) because it decides which pages are fetched and rendered."
todos:
  - id: matcher
    content: "robots_rules.py: group selection, rule parsing, wildcard and end-anchor patterns, longest-match decision"
    status: pending
  - id: cache
    content: "RobotsCache uses the matcher; status handling, public signature and error type unchanged"
    status: pending
  - id: fixtures
    content: "Four real robots.txt fixtures and expected verdicts"
    status: pending
  - id: repend
    content: "Operator re-pends robots failures once and records before and after counts"
    status: pending
isProject: false
---

# Chapter E10 — Robots rules fix

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `fix/extraction-robots-rules` · **Status:** planned

**Depends on:** crawlers [02](../../crawlers/chapters/02-fetcher-hardening.md) (the `RobotsCache`, merged) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes **second**, after [E11](11-free-tier-caps-95.md) and before E1. It is independent of E1 to E9, and every later chapter reads pages that this decision fetches or renders. Numbered E10 only so the chapter numbers already referenced elsewhere in the suite stay stable (the same device as crawlers chapter 23).

## Goal

Make the crawler's robots.txt verdict match what the site means. Today [`worker/robots.py`](../../../apps/discovery-ingest/discovery_ingest/worker/robots.py) delegates matching to Python's `urllib.robotparser`, which is wrong in two directions:

1. **First match wins.** `urllib` checks rules in file order. RFC 9309 says the **longest** matching rule wins and `Allow` wins a tie. A file that starts with `Disallow: /` and then lists `Allow:` paths blocks every page the site explicitly allows.
2. **`*` and `$` are not understood.** `Allow: /$` (home page only) becomes a literal path, so the home page is blocked; `Disallow: /*.pdf$` is ignored, so the crawler would **fetch** files the site forbids.

The second direction is a politeness bug, not only a coverage bug, so this is a correctness fix and not an optimisation.

### Evidence (checked 2026-10-28 with the shipped parser and the live files)

| Host | robots.txt rule | URL | Shipped verdict | RFC 9309 verdict |
| --- | --- | --- | --- | --- |
| `www.fuehrungszeugnis.bund.de` | `Disallow: /` then `Allow: /$` | `/` | blocked | **allowed** |
| `register.dpma.de` | `Disallow: /` then `Allow: /DPMAregister/Uebersicht` | `/DPMAregister/Uebersicht` | blocked | **allowed** |
| `www.bafin.de` | `Disallow: /SiteGlobals/` then `Allow: /SiteGlobals/Modules/` | `/SiteGlobals/Modules/x` | blocked | **allowed** |
| synthetic | `Disallow: /*.pdf$` | `/a.pdf` | allowed | **blocked** |

On 2026-10-28, 240 `fetch_url` tasks had failed (about 11 percent of the backlog). Only 8 of the 20 listed rows were probed. Those fell into correct failures (404 dead links, a 403 bot block, login redirect loops, a real `Disallow: /` as on `dipul.de`) and the robots rows above. How many of the 240 are robots false positives is **unknown**: the machine API does not return `last_error`, so the operator step below counts them instead of guessing.

## Contract

Two modules under `discovery_ingest/worker/`:

**`robots_rules.py`** (new, pure, no network):

```text
RobotsRules.parse(lines: Sequence[str], agent: str) -> RobotsRules
RobotsRules.allowed(url: str) -> bool
```

- **Lines:** `field: value`, `#` comments stripped, field names case-insensitive, unknown fields ignored (`Crawl-delay` is ignored; the `HostPacer` owns timing, crawlers chapter 2).
- **Groups:** consecutive `User-agent` lines share one rule list. The group for `agent` is the one whose token is the **longest case-insensitive prefix match** of the product token (`RedtapeBot`); groups naming the same agent are merged; if none match, the `*` group; if there is no `*` group, everything is allowed.
- **Patterns:** a rule path is a prefix pattern in which `*` matches any run of characters and a trailing `$` anchors the end. Matching runs against path plus query string. Percent-encodings compare case-insensitively on the hex digits; no other normalisation.
- **Decision:** among the rules that match, the one with the **longest pattern** wins (length in characters, `*` and `$` included); on a tie `Allow` wins; no match means allowed. An empty `Disallow:` value is "allow all" and is dropped. `/robots.txt` itself is always allowed.
- **Determinism:** the same lines and URL give the same verdict, independent of rule order in the file.

**`robots.py`** keeps its public surface: `RobotsCache(fetch, *, agent=BOT_PRODUCT_TOKEN)`, `allowed(url)`, `RobotsUnavailableError`. `_parse` builds a `RobotsRules` instead of a `RobotFileParser`. The status handling does not change: a client error (4xx) allows everything, a server error or transport failure raises `RobotsUnavailableError` (retryable, nothing fetched), the rules are cached per origin for the process. The failure message stays `robots.txt disallows <url>` with `FetchFailure.ROBOTS_DISALLOWED` (permanent), so the admin note chips and the operator SQL keep working.

**No new dependency.** The matcher is small (about forty lines in helpers of about five lines). **Swap point:** if it ever grows, `Protego` (RFC 9309, pure Python, no dependencies) can replace the body behind the same two-method interface; that swap is not planned here.

**Shared by both paths.** `PoliteUrlFetcher.check_robots` and the browser steps (`browser_steps.check_robots`, used by `render_page` and `capture_screenshot`) reach the same `RobotsCache`, so one change fixes plain fetches, renders and screenshots.

## TDD loops

### Loop A — Matching

**Red** (`apps/discovery-ingest/tests/test_robots_rules.py`, inline robots.txt lines)

1. `a longer allow beats a shorter disallow regardless of order in the file` (the DPMA and BaFin shapes).
2. `on equal length allow wins`.
3. `a trailing dollar anchors the end of the url` (`Allow: /$` allows `/` only, `Disallow: /*.pdf$` blocks `/a.pdf` and allows `/a.pdf?x=1`).
4. `a star matches any run of characters including slashes`.
5. `an empty disallow allows everything and an empty allow blocks nothing`.
6. `the most specific user agent group wins and falls back to the star group` and `groups naming the same agent are merged`.
7. `no matching group and no star group allows everything`.
8. `robots.txt itself is always allowed`.
9. `comments, blank lines, unknown fields and bad lines are ignored and never raise` — negative.
10. `the verdict does not depend on rule order` — property over a shuffled rule list.

**Green:** one helper per concern (clean lines, group select, compile pattern, decide). **Refactor:** helpers about five lines; the pattern compiler is a pure function from rule path to a regex or matcher; no nesting beyond one level.

### Loop B — Cache integration

**Red** (`tests/test_robots.py`, extend; the existing tests stay green)

1. `RobotsCache.allowed uses the new rules` (a fixture where first match and longest match disagree).
2. `a 4xx robots response allows everything` (unchanged, regression guard).
3. `a 5xx or transport failure raises RobotsUnavailableError and is cached per origin` (unchanged).
4. `the fetcher reports ROBOTS_DISALLOWED with the message robots.txt disallows <url> for a blocked url` (unchanged wording).
5. `a browser task with a blocked url fails permanently and an allowed url proceeds` — one test through `browser_steps.check_robots`.

**Green:** swap `_parse`. **Refactor:** delete the `RobotFileParser` import; no dead code.

### Loop C — Real files

**Red** (`tests/test_robots_fixtures.py`)

Fixtures under `apps/discovery-ingest/tests/fixtures/robots/`: the real `robots.txt` of `www.fuehrungszeugnis.bund.de`, `www.dipul.de`, `register.dpma.de` and `www.bafin.de`, captured 2026-10-28 with the date in a header comment (comments are ignored by the parser), trimmed only if very long. A table of expected verdicts is the test data:

1. `fuehrungszeugnis: / allowed, /anything-else blocked`.
2. `dipul: every path blocked` — a real `Disallow: /` stays blocked.
3. `dpma: / blocked, /DPMAregister/Uebersicht allowed`.
4. `bafin: /, /DE/Service allowed; /DE/_pgb/x, /Login/x blocked; /SiteGlobals/Modules/x allowed`.

**Green:** none expected beyond Loop A. **Refactor:** none.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_robots_rules.py tests/test_robots.py tests/test_robots_fixtures.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

**Live gate (operator, local, no Actions minutes).** Only the worker package changes, so nothing is deployed to Render. After the chapter merges:

```sql
-- how many tasks failed on robots (kinds that read robots.txt)
select kind, count(*) from discovery_task
where status = 'failed' and last_error like '%robots.txt disallows%'
group by 1;
```
```sql
-- re-pend them once; most will fail again, which is correct
update discovery_task
set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null,
    attempt_count = 0, not_before = null
where kind in ('fetch_url', 'render_page', 'capture_screenshot')
  and status = 'failed' and last_error like '%robots.txt disallows%';
```

Then drain the plain kind locally (`python -m discovery_ingest worker drain --kinds fetch_url --max-tasks 50 --max-batches 10 --time-budget-seconds 600`; render kinds wait for their daily browser budget) and run the first query again. Record in the [run ledger](../run-ledger.md): the count before, the count after, how many hosts flipped to allowed, and confirm that `dipul.de` still fails. A count that does not fall means the matcher is wrong or the sample was all real disallows; both are recorded, neither blocks a merge.

## Out of scope

`Crawl-delay` and `Request-rate` (the per-host pacer owns timing), `Sitemap:` discovery, `X-Robots-Tag` and `<meta name="robots">` handling, caching robots.txt across processes or days, a per-host override list, changing the bot token or user agent, and the 403/login-wall/redirect-loop failures (those are correct).
