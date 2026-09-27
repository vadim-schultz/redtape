---
name: "Chapter 4 — Source registry"
overview: "sources.yaml lists what to crawl (jurisdiction, start URL, extractor id); load_sources validates it at load time so a typo fails fast instead of during a scheduled run."
todos:
  - id: schema
    content: "Source dataclass and Pydantic-validated YAML loader"
    status: pending
  - id: registry
    content: "load_sources with clear validation errors"
    status: pending
isProject: false
---

# Chapter 4 — Source registry

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-source-registry` · **Status:** planned

**Depends on:** [1](01-crawler-package-skeleton.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`load_sources(path) -> list[Source]` reads `sources.yaml` and fails with a clear, specific error before any
network call, so a scheduled run never gets partway through and dies on a typo.

## Design decisions

**Shape**: `Source(id: str, jurisdiction_id: UUID, start_url: HttpUrl, extractor: str, enabled: bool =
True)`. `id` is unique (checked at load); `jurisdiction_id` is not validated against the database here (the
registry has no database access, D3) — an unknown jurisdiction surfaces later as a 422 from the suggestion
API (suggestion-interface's own validation), and the orchestrator's report (chapter 9) makes that failure
visible per source.

**Validation via Pydantic**, reusing the same library the API already depends on conceptually (not
literally shared code — `apps/crawler` has its own `pyproject.toml`, D2 — but the same validate-at-the-edge
discipline).

**`enabled: false`** lets a source be kept in the file (documentation of what exists) without running it —
useful while an extractor is still being built (chapters 5–6 land before a source is flipped on).

**One real entry at first** (chapter 6 supplies it); the registry itself is exercised with fixture YAML in
this chapter's tests, not the real file, so a later addition to `sources.yaml` cannot break this chapter's
tests by construction.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/crawler/sources.py` | `Source`, `load_sources` |
| `apps/crawler/sources.yaml` | Starts with zero or one disabled placeholder entry |
| `apps/crawler/tests/test_sources.py` | Tests below (fixture YAML strings, not the real file) |
| `apps/crawler/tests/fixtures/sources/*.yaml` | Fixture files |

## Red tests

| Test | Asserts |
| --- | --- |
| `load_sources · parses a valid file into Source objects` | Fields match |
| `load_sources · rejects a duplicate id` | Clear error message names the id |
| `load_sources · rejects a non-http start_url` | Validation error |
| `load_sources · rejects an unparseable jurisdiction_id` | Validation error |
| `load_sources · rejects a source referencing no extractor field` | Missing required field |
| `load_sources · defaults enabled to true when omitted` | Default |
| `load_sources · rejects a malformed YAML file with a clear error, not a stack trace` | Wrapped exception |
| `load_sources · an empty file yields an empty list, not an error` | Boundary |

## Green

1. `Source` model and happy-path parsing; tests 1, 6, 8.
2. Per-field validation; tests 3–5.
3. Duplicate-id check; test 2.
4. YAML error wrapping; test 7.

## Refactor gate

`load_sources` is load-then-validate-then-check-duplicates, three named steps. Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_sources.py -m "not needs_playwright"
```

## Out of scope

Extraction (chapter 5), the real first source (chapter 6).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-source-registry
```

```text
test(crawler): describe source validation and duplicate-id detection

feat(crawler): add the source registry
```
