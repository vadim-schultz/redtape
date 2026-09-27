---
name: "Chapter 6 — First extractor"
overview: "One real extractor for one real government source, built against a saved fixture of its actual HTML, enabled in sources.yaml; the open seam S1 (which source) is resolved here, not before."
todos:
  - id: choose
    content: "Pick the first source and save a fixture of its real markup"
    status: pending
  - id: extractor
    content: "Implement and register the extractor"
    status: pending
isProject: false
---

# Chapter 6 — First extractor

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-first-extractor` · **Status:** planned

**Depends on:** [5](05-extractor-interface-and-fixtures.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

One working extractor against a real site, resolving the program's open seam S1 ("which source the first
crawler targets"). This is the chapter where the suite stops being infrastructure and produces its first
real candidates.

## Design decisions

**Source choice is a decision for this chapter, not earlier ones.** A good first candidate: a municipal or
federal portal with a stable, simple listing page (a table or list of document types with links), matching
one of the jurisdictions already seeded by OpenPLZ import
([import_openplz_locations.py](../../../apps/api/scripts/import_openplz_locations.py)) so the submitted
suggestion's `jurisdiction_id` resolves against real seeded data. The specific site is chosen and recorded
here (not earlier) because it is exactly the kind of decision the program plan flagged as an open seam
depending on product input, not architecture.

**Fixture-first.** The real page's HTML is fetched once by hand (or via a one-off script, not committed),
saved as `tests/fixtures/html/<extractor-id>/listing.html`, and the extractor is built entirely against
that saved copy — no test in this suite makes a real network request (matching invariant 2 of the
rollout). A second fixture captures an edge case observed in the real page (e.g. an entry with a relative
URL, or a row with no link) so the extractor handles it deliberately, not by luck.

**Extractor logic** stays a straightforward parse (`selectolax` or `lxml`, whichever `apps/api` and the
ecosystem already favor — checked against existing dependencies before choosing, since neither is currently
used anywhere in the repo and this is a new dependency either way): find the listing rows, pull title and
link, resolve relative URLs against the source's `start_url`, skip rows with no usable link (documented,
not silently swallowed — counted in the orchestrator's report later).

**`sources.yaml`** gains one real, `enabled: true` entry.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/pyproject.toml` | HTML parsing dependency |
| `apps/crawler/crawler/extractors/<source_id>.py` | The extractor |
| `apps/crawler/tests/fixtures/html/<source_id>/{listing,edge-case}.html` | Saved real markup |
| `apps/crawler/sources.yaml` | One enabled entry |
| `apps/crawler/tests/test_<source_id>_extractor.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `<source> extractor · extracts every document row from the listing fixture` | Count and titles match a hand-verified fixture |
| `<source> extractor · resolves a relative link against the source's start_url` | Absolute URL produced |
| `<source> extractor · skips a row with no usable link` | Documented, not raised |
| `<source> extractor · registers under the id sources.yaml references` | `EXTRACTORS["<id>"]` is this extractor |
| `<source> extractor · produces candidates that pass DocumentCandidate validation` | No construction error |

## Green

1. Fixture files and hand-verified expected output.
2. Extractor happy path; test 1.
3. Relative-URL and skip handling; tests 2–3.
4. Registration and `sources.yaml`; tests 4–5.

## Refactor gate

Extractor stays one file, ≤ ~80 LOC; row-parsing logic is one named helper, not inlined in `extract`.
Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_<source_id>_extractor.py -m "not needs_playwright"
```

Manual: run `python -m crawler.run --source <source_id> --dry-run` (chapter 9) once the orchestrator exists,
to confirm the extractor still matches the live page's current markup (fixtures can drift from reality).

## Out of scope

Screenshot capture (chapter 7), submission (chapters 8–9).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-first-extractor
```

```text
test(crawler): describe extracting documents from <source>'s listing page

feat(crawler): add the first real extractor for <source>
```
