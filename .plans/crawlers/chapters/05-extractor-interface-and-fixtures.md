---
name: "Chapter 5 — Extractor interface and fixtures"
overview: "The Extractor protocol and DocumentCandidate shape, a registry that dispatches by source, and a saved-fixture testing convention — everything a real extractor needs, proven against a fake extractor before any real HTML exists."
todos:
  - id: protocol
    content: "Extractor protocol, DocumentCandidate, EXTRACTORS registry"
    status: pending
  - id: fixture-convention
    content: "tests/fixtures/html/ convention and a fake extractor exercising it"
    status: pending
isProject: false
---

# Chapter 5 — Extractor interface and fixtures

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-extractor-interface` · **Status:** planned

**Depends on:** [3](03-polite-fetcher.md), [4](04-source-registry.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The shape every extractor implements, dispatched from a source's `extractor` id, and a fixture-based testing
convention — proven with a throwaway fake extractor so chapter 6 is purely "write one real one," no
framework decisions left.

## Design decisions

**`DocumentCandidate`**: `title: str`, `description: str | None`, `official_url: str`, `source_url: str`
(the page it was found on — may differ from `official_url` for a listing page linking elsewhere).

**`Extractor` protocol**: `id: str` (matches a source's `extractor` field), `extract(html: str, source:
Source) -> list[DocumentCandidate]`. Pure function of HTML text in, candidates out — no network, no
filesystem, so any extractor is unit-testable purely with a saved HTML string.

**`EXTRACTORS: dict[str, Extractor]`** keyed by id; `get_extractor(source) -> Extractor` raises
`UnknownExtractorError` for a registry/source mismatch (surfaces as a per-source failure in the
orchestrator's report, chapter 9, not a crash of the whole run).

**Fixture convention**: `tests/fixtures/html/<extractor-id>/<case>.html`, saved real (or representative)
markup, loaded by a small `load_fixture(extractor_id, case)` helper. This chapter proves the convention with
`tests/fixtures/html/fake/simple.html` and a `FakeExtractor` that only exists in tests.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/crawler/extractors/base.py` | `DocumentCandidate`, `Extractor` protocol, `EXTRACTORS`, `get_extractor` |
| `apps/crawler/tests/support/fixtures.py` | `load_fixture` |
| `apps/crawler/tests/fixtures/html/fake/simple.html` | Fixture |
| `apps/crawler/tests/test_extractor_registry.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `get_extractor · dispatches to the extractor matching the source's extractor id` | Correct instance |
| `get_extractor · raises UnknownExtractorError for an unregistered id` | Negative |
| `load_fixture · reads the saved HTML file for an extractor and case` | Content matches |
| `FakeExtractor · extract returns candidates parsed from the fixture` | Proves the whole convention end to end |
| `DocumentCandidate · requires a non-blank title and official_url` | Construction validation |

## Green

1. `DocumentCandidate` and its validation; test 5.
2. Protocol, registry, dispatch; tests 1–2.
3. Fixture helper and fake extractor; tests 3–4.

## Refactor gate

`get_extractor` is a one-line dict lookup with a clear error; no premature base class beyond the protocol.
Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_extractor_registry.py -m "not needs_playwright"
```

## Out of scope

The real extractor (chapter 6), calling any of this from the orchestrator (chapter 9).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-extractor-interface
```

```text
test(crawler): describe extractor dispatch and the fixture convention

feat(crawler): add the Extractor protocol and registry
```
