---
name: "Chapter E2 — Page cleaner"
overview: "A deterministic clean_page function that turns a rendered DOM into compact markdown plus its link set, with section prioritisation under a character cap and a recall gate on real fixtures."
todos:
  - id: cleaner
    content: "clean_page: boilerplate drop, main-content preference, compact markdown, link set, language"
    status: pending
  - id: cap
    content: "Character cap with section prioritisation and truncated flag"
    status: pending
  - id: fixtures
    content: "Fixtures from real snapshots and a recall gate"
    status: pending
isProject: false
---

# Chapter E2 — Page cleaner

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-page-cleaner` · **Status:** planned

**Depends on:** crawlers [07](../../crawlers/chapters/07-pvog-payload-harvester.md) (the HTML parser dependency), [17](../../crawlers/chapters/17-extractor-framework.md) (the decode function) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Free neurons are the scarce resource, so the model should read the part of the page that matters and nothing else. The cleaner removes boilerplate, keeps structure (headings, lists, tables, link targets) and reports the page's links, which the grounding step later uses to accept or null URLs. It makes no network call and has no model in it.

## Contract

`discovery_ingest/extract/clean.py`:

```text
clean_page(html: str, base_url: str, *, max_chars: int = 12000) -> CleanPage
CleanPage: text: str, links: frozenset[str], language: str | None, title: str | None, truncated: bool, version: str
```

- **Drop:** `script`, `style`, `noscript`, `template`, `svg`, `nav`, `header`, `footer`, `aside`, `form` (except inside the main region), elements whose id or class matches a small cookie/consent/search/breadcrumb list, hidden elements (`hidden`, `aria-hidden="true"`).
- **Main region:** prefer `main`, `[role=main]`, `article` when its text is at least 600 characters; otherwise use `body`.
- **Markdown:** headings as `#` lines, list items as `- `, table rows as `a | b | c`, definition lists as `term: text`, links as `text (url)` with absolute URLs; whitespace collapsed; consecutive duplicate lines removed.
- **Links:** every absolute `http`/`https` link in the **whole** document (not only the kept region), resolved against `base_url`, fragments dropped; `mailto:` and `javascript:` excluded.
- **Language:** `<html lang>` reduced to its primary subtag, else `None` (the caller defaults to `de`).
- **Cap:** when the text exceeds `max_chars`, split into sections by heading, keep first the sections whose heading matches `unterlagen|nachweis|voraussetzung|formular|erforderlich|mitbring|antrag|dokument`, then the rest in document order, until the cap; `truncated = True`. Never cut inside a line.
- **Version:** a constant (`"clean-1"`) bumped on any rule change; it is part of the extraction `input_key` lineage (chapter E7) so a cleaner change is visible in the ledger.
- Pure and deterministic: the same input gives the same output, in the same order.

**Swap point.** The signature is the contract. If the eval (chapter E5) shows poor recall or avoidable token cost, the body is reimplemented on Trafilatura (`favor_recall=True`, markdown output) behind the same function and `version` changes. That swap is not planned here.

**Fixtures** under `apps/discovery-ingest/tests/fixtures/pages/`: five to eight **rendered snapshots** captured with the crawlers fixture-capture workflow (chapter 17) from different hosts (an accordion-style service page, a list page, a JavaScript shell, a page with a large footer and cookie banner), trimmed in size, personal data removed. Each has a small expected-facts file listing sentences and document names that must survive cleaning (for example `Personalausweis`, `Meldebescheinigung`).

## TDD loops

### Loop A — Cleaning

**Red** (`apps/discovery-ingest/tests/test_clean_page.py`, small inline HTML)

1. `boilerplate elements and hidden elements are dropped`.
2. `main region is preferred when long enough and the body is used otherwise`.
3. `headings, list items, table rows and links become compact markdown with absolute urls`.
4. `links include anchors outside the kept region and exclude mailto, javascript and fragments`.
5. `language is read from the html lang attribute and is none when absent`.
6. `output is deterministic and collapses whitespace and duplicate lines`.
7. `malformed or empty html returns empty text without raising` — negative.

**Green:** one function per concern (drop, region, markdown, links). **Refactor:** each helper about five lines; selectors as named constants.

### Loop B — Cap and prioritisation

**Red** (`test_clean_page_cap.py`)

1. `text under the cap is returned whole with truncated false`.
2. `over the cap, sections whose headings match the priority words are kept first`.
3. `the cap never cuts a line and truncated is true`.
4. `a page with no priority headings keeps the leading sections in order`.

**Green:** section splitter and a budgeted join. **Refactor:** priority words in one tuple.

### Loop C — Recall gate

**Red** (`test_clean_page_fixtures.py`)

1. `every expected fact of every fixture survives cleaning` — recall 1.0 on the listed facts.
2. `cleaned text is at most 40 percent of the raw text length on average across fixtures` — the token-saving guard; a failing ratio is reported, not hidden.
3. `the javascript shell fixture yields more text than its raw response` (it is a rendered snapshot).

**Green:** adjust rules until the gate passes. **Refactor:** none expected beyond naming.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_clean_page.py tests/test_clean_page_cap.py tests/test_clean_page_fixtures.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate: after crawlers chapter 15's live render, run `discovery-fixture-capture.yml` for two hosts, run `clean_page` over the downloads from a Python shell and record characters before and after and whether the expected document names survive. If fixtures cannot be captured yet, the chapter merges on synthetic fixtures with the gate recorded as deferred; chapter E5 re-runs it on real snapshots.

## Out of scope

Calling a model, token counting with a real tokenizer (characters are the budget unit), PDF text, language detection beyond `<html lang>`, Trafilatura (a swap, not part of this chapter).
